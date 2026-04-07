import json
from typing import Any, Dict, List, Optional, Union

import torch
import torch.nn as nn
from transformers import RobertaModel


def save_json(data: Any, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def decode_spans(
    start_logits: torch.Tensor,
    end_logits: torch.Tensor,
    k: int = 5,
    max_span_len: int = 20
) -> List[tuple[int, int, float]]:
    start_probs = torch.sigmoid(start_logits)
    end_probs = torch.sigmoid(end_logits)

    top_starts: torch.Tensor = torch.topk(start_probs, k).indices
    top_ends: torch.Tensor = torch.topk(end_probs, k).indices

    spans: List[tuple[int, int, float]] = []

    for s_t in top_starts:
        s: int = int(s_t.item())
        for e_t in top_ends:
            e: int = int(e_t.item())
            if s <= e and (e - s) <= max_span_len:
                score = start_probs[s] * end_probs[e]
                spans.append((s, e, float(score.item())))

    spans = sorted(spans, key=lambda x: x[2], reverse=True)
    return spans[:k]


def classify_spans(
    model: "SpanTSA",
    hidden_states: torch.Tensor,
    spans: List[tuple[int, int, float]]
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for s, e, score in spans:
        # Add batch dim
        span_repr: torch.Tensor = hidden_states[s:e+1].mean(dim=0).unsqueeze(0)
        logits: torch.Tensor = model.span_classifier(span_repr).squeeze(0)
        pred: int = int(torch.argmax(logits).item())

        results.append({
            "start": int(s),
            "end": int(e),
            "polarity": pred + 2,
            "confidence": float(score)
        })

    return results


def normalize_score(p: float) -> float:
    # 2 → -1, 6 → 1
    return (p - 4) / 2


def aggregate_document(spans: List[Dict[str, Any]]) -> Optional[float]:
    if not spans:
        return None
    scores: List[float] = [normalize_score(s["polarity"]) for s in spans]
    return sum(scores) / len(scores)


def update_document(
    output: List[Dict[str, Any]],
    input_data: List[Dict[str, Any]],
    num_classes: int = 3
) -> List[Dict[str, Any]]:
    assert num_classes in (3, 5), f"Input should be 3 or 5, was {num_classes}"

    for item, y in zip(output, input_data, strict=True):
        sentiment: Union[float, None] = item["document_sentiment"]
        if sentiment is not None:
            assert -1 <= sentiment <= 1, "Sentiment should be between -1 and 1"

        if sentiment is None:
            y["sentiment_label"] = None
        elif num_classes == 3:
            if sentiment < -0.33:
                y["sentiment_label"] = "NEGATIVE"
            elif sentiment >= 0.3:
                y["sentiment_label"] = "POSITIVE"
            else:
                y["sentiment_label"] = "NEUTRAL"
        else:
            if sentiment < -0.6:
                y["sentiment_label"] = "VERY_NEGATIVE"
            elif sentiment < -0.2:
                y["sentiment_label"] = "SOMEWHAT_NEGATIVE"
            elif sentiment < 0.2:
                y["sentiment_label"] = "NEUTRAL"
            elif sentiment < 0.6:
                y["sentiment_label"] = "SOMEWHAT_POSITIVE"
            else:
                y["sentiment_label"] = "VERY_POSITIVE"

        y["sentiment_score"] = sentiment

    return input_data


class SpanTSA(nn.Module):
    def __init__(self, model_name: str = "roberta-base", num_labels: int = 5) -> None:
        super().__init__()
        self.encoder: RobertaModel = RobertaModel.from_pretrained(model_name)
        hidden: int = self.encoder.config.hidden_size

        # Span detection
        self.start_classifier: nn.Linear = nn.Linear(hidden, 1)
        self.end_classifier: nn.Linear = nn.Linear(hidden, 1)

        # Sentiment classifier
        self.span_classifier: nn.Sequential = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden, num_labels)
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        start_positions: Optional[torch.Tensor] = None,
        end_positions: Optional[torch.Tensor] = None,
        span_labels: Optional[List[List[tuple[int, int, int]]]] = None
    ) -> Dict[str, torch.Tensor]:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        hidden_states: torch.Tensor = outputs.last_hidden_state

        start_logits: torch.Tensor = self.start_classifier(hidden_states).squeeze(-1)
        end_logits: torch.Tensor = self.end_classifier(hidden_states).squeeze(-1)

        loss: torch.Tensor = torch.tensor(0.0, device=input_ids.device)

        if start_positions is not None and end_positions is not None:
            loss_fn_bce: nn.BCEWithLogitsLoss = nn.BCEWithLogitsLoss()
            loss += loss_fn_bce(start_logits, start_positions.float())
            loss += loss_fn_bce(end_logits, end_positions.float())

        if span_labels is not None:
            span_loss: torch.Tensor = torch.tensor(0.0, device=input_ids.device)
            count: int = 0
            loss_fn_ce: nn.CrossEntropyLoss = nn.CrossEntropyLoss()

            for b in range(len(span_labels)):
                for s, e, label in span_labels[b]:
                    span_repr: torch.Tensor = (hidden_states[b, s:e+1].
                                               mean(dim=0).unsqueeze(0))
                    logits: torch.Tensor = self.span_classifier(span_repr).squeeze(0)
                    target: torch.Tensor = torch.tensor([label], device=logits.device)
                    span_loss += loss_fn_ce(logits.unsqueeze(0), target)
                    count += 1

            if count > 0:
                loss += span_loss / count

        return {
            "loss": loss,
            "start_logits": start_logits,
            "end_logits": end_logits,
        }