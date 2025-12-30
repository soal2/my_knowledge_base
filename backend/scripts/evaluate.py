"""
RAGAS Evaluation Script for the Knowledge Base RAG System

This script evaluates the quality of RAG responses using RAGAS metrics:
- Faithfulness: Does the answer accurately reflect the context?
- Context Precision: Is the retrieved context relevant?
- Context Recall: Does the context contain the answer?
- Answer Relevancy: Is the answer relevant to the question?

Usage:
    python -m scripts.evaluate --samples 50 --output results.json
    python -m scripts.evaluate --dataset eval_data.json
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings

from flask import Flask
from config import Config
from database.models import db, ChatSession, ChatMessage, FileDocument, MessageRole
from services.retrieval import RetrievalService
from agent.graph import KnowledgeBaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EvalSample:
    """A single evaluation sample."""
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvalResult:
    """Evaluation result with metrics."""
    timestamp: str
    num_samples: int
    metrics: Dict[str, float]
    samples: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'num_samples': self.num_samples,
            'metrics': self.metrics,
            'samples': self.samples
        }


# =============================================================================
# Evaluation Data Collection
# =============================================================================

def collect_evaluation_data_from_db(
    user_id: int,
    limit: int = 100
) -> List[EvalSample]:
    """
    Collect evaluation samples from database chat history.
    
    Args:
        user_id: User ID to evaluate
        limit: Maximum samples to collect
        
    Returns:
        List of EvalSample objects
    """
    samples = []
    retrieval_service = RetrievalService()
    
    # Get recent chat messages
    sessions = ChatSession.query.filter_by(
        user_id=user_id,
        is_archived=False
    ).order_by(ChatSession.last_active_at.desc()).limit(20).all()
    
    for session in sessions:
        messages = ChatMessage.query.filter_by(
            session_id=session.id
        ).order_by(ChatMessage.created_at).all()
        
        # Pair user messages with AI responses
        for i in range(len(messages) - 1):
            if messages[i].role == MessageRole.USER and \
               messages[i+1].role == MessageRole.AI:
                
                question = messages[i].content
                answer = messages[i+1].content
                
                # Retrieve context for this question
                result = retrieval_service.hybrid_retrieve(
                    query=question,
                    user_id=user_id,
                    top_k=5
                )
                
                contexts = result.get('documents', [])
                
                samples.append(EvalSample(
                    question=question,
                    answer=answer,
                    contexts=contexts
                ))
                
                if len(samples) >= limit:
                    return samples
    
    return samples


def load_evaluation_dataset(filepath: str) -> List[EvalSample]:
    """
    Load evaluation dataset from JSON file.
    
    Expected format:
    [
        {
            "question": "...",
            "answer": "...",
            "contexts": ["...", "..."],
            "ground_truth": "..." (optional)
        }
    ]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    samples = []
    for item in data:
        samples.append(EvalSample(
            question=item['question'],
            answer=item['answer'],
            contexts=item.get('contexts', []),
            ground_truth=item.get('ground_truth')
        ))
    
    return samples


def generate_evaluation_data(
    user_id: int,
    agent: KnowledgeBaseAgent,
    questions: List[str],
    provider: str = "qwen"
) -> List[EvalSample]:
    """
    Generate evaluation data by running agent on questions.
    
    Args:
        user_id: User ID
        agent: KnowledgeBaseAgent instance
        questions: List of questions to evaluate
        provider: LLM provider
        
    Returns:
        List of EvalSample objects
    """
    samples = []
    retrieval_service = RetrievalService()
    
    for question in questions:
        # Get answer from agent
        result = agent.chat(
            user_id=user_id,
            session_id=0,  # Dummy session for evaluation
            query=question,
            provider=provider
        )
        
        # Get retrieved contexts
        retrieval_result = retrieval_service.hybrid_retrieve(
            query=question,
            user_id=user_id,
            top_k=5
        )
        
        samples.append(EvalSample(
            question=question,
            answer=result.get('response', ''),
            contexts=retrieval_result.get('documents', [])
        ))
    
    return samples


# =============================================================================
# RAGAS Evaluation
# =============================================================================

def setup_ragas_evaluator(
    llm_provider: str = "deepseek",
    api_key: Optional[str] = None
) -> tuple:
    """
    Setup LLM and embeddings for RAGAS evaluation.
    
    Args:
        llm_provider: LLM provider to use for evaluation
        api_key: API key for the LLM
        
    Returns:
        Tuple of (llm, embeddings)
    """
    # Default model and base_url
    model = "deepseek-chat"
    base_url = "https://api.deepseek.com/v1"
    
    # Get API key from environment if not provided
    if api_key is None:
        if llm_provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = "https://api.deepseek.com/v1"
            model = "deepseek-chat"
        else:
            api_key = os.getenv("DASHSCOPE_API_KEY")
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            model = "qwen-plus"
    
    # Setup LLM
    llm = ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0
    )
    
    # Setup embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    return (
        LangchainLLMWrapper(llm),
        LangchainEmbeddingsWrapper(embeddings)
    )


def run_ragas_evaluation(
    samples: List[EvalSample],
    llm_provider: str = "deepseek",
    api_key: Optional[str] = None,
    metrics: Optional[List] = None
) -> EvalResult:
    """
    Run RAGAS evaluation on samples.
    
    Args:
        samples: List of EvalSample objects
        llm_provider: LLM provider for evaluation
        api_key: API key
        metrics: List of RAGAS metrics to use
        
    Returns:
        EvalResult with metrics and per-sample scores
    """
    logger.info(f"Running RAGAS evaluation on {len(samples)} samples")
    
    if metrics is None:
        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]
    
    # Setup evaluator
    llm, embeddings = setup_ragas_evaluator(llm_provider, api_key)
    
    # Prepare dataset
    eval_data = {
        'question': [],
        'answer': [],
        'contexts': [],
        'ground_truth': []
    }
    
    for sample in samples:
        eval_data['question'].append(sample.question)
        eval_data['answer'].append(sample.answer)
        eval_data['contexts'].append(sample.contexts)
        eval_data['ground_truth'].append(sample.ground_truth or sample.answer)
    
    dataset = Dataset.from_dict(eval_data)
    
    # Run evaluation
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings
    )
    
    # Extract metrics
    metrics_dict = {
        'faithfulness': float(result['faithfulness']),
        'answer_relevancy': float(result['answer_relevancy']),
        'context_precision': float(result['context_precision']),
        'context_recall': float(result['context_recall'])
    }
    
    # Create result object
    eval_result = EvalResult(
        timestamp=datetime.utcnow().isoformat(),
        num_samples=len(samples),
        metrics=metrics_dict,
        samples=[s.to_dict() for s in samples]
    )
    
    return eval_result


# =============================================================================
# Reporting
# =============================================================================

def print_evaluation_report(result: EvalResult):
    """Print a formatted evaluation report."""
    print("\n" + "=" * 60)
    print("RAGAS EVALUATION REPORT")
    print("=" * 60)
    print(f"Timestamp: {result.timestamp}")
    print(f"Samples Evaluated: {result.num_samples}")
    print("-" * 60)
    print("\nMETRICS:")
    print("-" * 40)
    
    for metric, score in result.metrics.items():
        # Color coding based on score
        if score >= 0.8:
            status = "✅"
        elif score >= 0.6:
            status = "⚠️"
        else:
            status = "❌"
        
        print(f"  {status} {metric.replace('_', ' ').title()}: {score:.4f}")
    
    print("-" * 60)
    
    # Overall score
    overall = sum(result.metrics.values()) / len(result.metrics)
    print(f"\n📊 Overall Score: {overall:.4f}")
    
    # Interpretation
    print("\n📋 Interpretation:")
    if overall >= 0.8:
        print("  Excellent - The RAG system is performing well across all metrics.")
    elif overall >= 0.6:
        print("  Good - The system works but has room for improvement.")
    else:
        print("  Needs Improvement - Consider tuning retrieval and generation.")
    
    print("\n" + "=" * 60)


def save_evaluation_report(result: EvalResult, filepath: str):
    """Save evaluation results to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    
    logger.info(f"Evaluation report saved to {filepath}")


# =============================================================================
# CLI
# =============================================================================

def create_app_context():
    """Create Flask app context for database access."""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def main():
    parser = argparse.ArgumentParser(
        description="RAGAS Evaluation for Knowledge Base RAG System"
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        default=1,
        help="User ID to evaluate (default: 1)"
    )
    
    parser.add_argument(
        '--samples',
        type=int,
        default=50,
        help="Number of samples to evaluate (default: 50)"
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        help="Path to evaluation dataset JSON file"
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        help="Output file for results"
    )
    
    parser.add_argument(
        '--provider',
        type=str,
        choices=['qwen', 'deepseek'],
        default='deepseek',
        help="LLM provider for evaluation (default: deepseek)"
    )
    
    parser.add_argument(
        '--questions-file',
        type=str,
        help="Path to file with questions to generate answers for"
    )
    
    args = parser.parse_args()
    
    # Create app context
    app = create_app_context()
    
    with app.app_context():
        # Collect samples
        if args.dataset:
            logger.info(f"Loading evaluation dataset from {args.dataset}")
            samples = load_evaluation_dataset(args.dataset)
        elif args.questions_file:
            logger.info(f"Generating answers for questions in {args.questions_file}")
            with open(args.questions_file, 'r') as f:
                questions = [line.strip() for line in f if line.strip()]
            agent = KnowledgeBaseAgent()
            samples = generate_evaluation_data(
                user_id=args.user_id,
                agent=agent,
                questions=questions,
                provider=args.provider
            )
        else:
            logger.info(f"Collecting {args.samples} samples from database")
            samples = collect_evaluation_data_from_db(
                user_id=args.user_id,
                limit=args.samples
            )
        
        if not samples:
            logger.error("No samples found for evaluation")
            sys.exit(1)
        
        logger.info(f"Collected {len(samples)} samples")
        
        # Run evaluation
        result = run_ragas_evaluation(
            samples=samples,
            llm_provider=args.provider
        )
        
        # Print and save report
        print_evaluation_report(result)
        save_evaluation_report(result, args.output)


if __name__ == "__main__":
    main()
