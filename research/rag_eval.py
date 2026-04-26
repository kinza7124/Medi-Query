import json
import os
import sys
from dataclasses import dataclass
from typing import List

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import app


@dataclass
class TestCase:
    question: str
    expected_keywords: List[str]
    out_of_scope: bool = False


TEST_CASES: List[TestCase] = [
    TestCase("What is acne?", ["skin", "pimples", "pores"]),
    TestCase("What is diabetes?", ["blood sugar", "type i", "type ii"]),
    TestCase("What is hypertension?", ["blood pressure"]),
    TestCase("What is asthma?", ["airway", "breathing"]),
    TestCase("What is migraine?", ["headache"]),
    TestCase("What is tuberculosis?", ["bacteria", "lungs"]),
    TestCase("What is anemia?", ["hemoglobin", "red blood"]),
    TestCase("What is stroke?", ["brain", "blood supply"]),
    TestCase("Who is Kinza?", [], out_of_scope=True),
]


ABSTAIN_MARKERS = [
    "i don't know",
    "i do not know",
    "based on the provided context",
    "not in the provided context",
]


def keyword_recall(text: str, keywords: List[str]) -> float:
    if not keywords:
        return 1.0
    lower_text = text.lower()
    matches = sum(1 for keyword in keywords if keyword.lower() in lower_text)
    return matches / len(keywords)


def is_abstained(answer: str) -> bool:
    lower_answer = answer.lower()
    return any(marker in lower_answer for marker in ABSTAIN_MARKERS)


def main() -> None:
    rows = []

    for case in TEST_CASES:
        response = app.rag_chain.invoke({"input": case.question})
        answer = str(response.get("answer", ""))

        context_docs = response.get("context", [])
        context_text = "\n".join(getattr(doc, "page_content", "") for doc in context_docs)

        answer_recall = keyword_recall(answer, case.expected_keywords)
        context_recall = keyword_recall(context_text, case.expected_keywords)

        abstained = is_abstained(answer)
        oos_ok = (not case.out_of_scope) or abstained

        rows.append(
            {
                "question": case.question,
                "out_of_scope": case.out_of_scope,
                "answer": answer,
                "answer_keyword_recall": round(answer_recall, 3),
                "context_keyword_recall": round(context_recall, 3),
                "abstained": abstained,
                "oos_ok": oos_ok,
            }
        )

    in_domain = [row for row in rows if not row["out_of_scope"]]
    oos = [row for row in rows if row["out_of_scope"]]

    summary = {
        "num_tests": len(rows),
        "num_in_domain": len(in_domain),
        "num_out_of_scope": len(oos),
        "avg_answer_keyword_recall": round(
            sum(row["answer_keyword_recall"] for row in in_domain) / max(len(in_domain), 1),
            3,
        ),
        "avg_context_keyword_recall": round(
            sum(row["context_keyword_recall"] for row in in_domain) / max(len(in_domain), 1),
            3,
        ),
        "in_domain_pass_rate_at_0_5": round(
            sum(1 for row in in_domain if row["answer_keyword_recall"] >= 0.5)
            / max(len(in_domain), 1),
            3,
        ),
        "oos_abstain_accuracy": round(
            sum(1 for row in oos if row["oos_ok"]) / max(len(oos), 1),
            3,
        ),
    }

    print("=== RAG EVAL SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("\n=== PER-QUESTION RESULTS ===")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
