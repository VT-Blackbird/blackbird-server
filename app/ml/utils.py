import json
from typing import Any, Dict, List

import torch
import torch.nn as nn
from transformers import RobertaModel


def save_json(data:Any, filename:str)->None:
    with open(filename, "w", encoding = "utf-8") as f:
        json.dump(data, f, indent = 2, ensure_ascii=False)

def decode_spans(start_logits, end_logits, k=5, max_span_len=20):
    start_probs = torch.sigmoid(start_logits)
    end_probs = torch.sigmoid(end_logits)

    top_starts = torch.topk(start_probs, k).indices
    top_ends = torch.topk(end_probs, k).indices

    spans = []

    for s in top_starts:
        for e in top_ends:
            if s <= e and (e - s) <= max_span_len:
                score = start_probs[s] * end_probs[e]
                spans.append((s.item(), e.item(), score.item()))

    spans = sorted(spans, key=lambda x: x[2], reverse=True)
    return spans[:k]
def classify_spans(model, hidden_states, spans):
    results = []

    for (s, e, score) in spans:
        span_repr = hidden_states[s:e+1].mean(dim=0)
        logits = model.span_classifier(span_repr)
        pred = torch.argmax(logits).item()

        results.append({
            "start": s,
            "end": e,
            "polarity": pred + 2,  # back to 2–6
            "confidence": score
        })

    return results

def normalize_score(p):
    # 2 → -1, 6 → 1
    return (p - 4) / 2

def aggregate_document(spans):
    if not spans:
        return None

    scores = [normalize_score(s["polarity"]) for s in spans]
    return sum(scores) / len(scores)

#update original
#output is ML model output, input_data is the dataset
# we input to ml model, num classes is the thresholding
def update_document(output:List[Dict[str, Any]],
                    input_data:List[Dict[str,Any]],
                    num_classes = 3)->List[Dict[str, Any]]:
    #check num_classes is 3 or 5, no other valid int
    assert num_classes == 3 or num_classes == 5,\
        f"Input should be 3 or 5, was {num_classes}"
    #loop through each dict in input_document
    for item,y in zip(output, input_data, strict = True):
        #get "document_sentiment" at that index of output
        sentiment:float = item["document_sentiment"]
        assert (sentiment is None) or (sentiment <=1 and sentiment >=-1), \
            "Sentiment should be between -1 and 1"
        if sentiment is None:
            #add to doc "NA"
            y["sentiment_label"] = "NA"
        elif num_classes == 3:
            if sentiment < -0.33:#neg case
                y["sentiment_label"] = "NEGATIVE"
            elif sentiment >= 0.3: #positive case
                y["sentiment_label"] = "POSITIVE"
            else: #neutral case
                y["sentiment_label"] = "NEUTRAL"
        else: #five classes
            if sentiment < -0.6: #very negative
                y["sentiment_label"] = "VERY_NEGATIVE"
            elif sentiment >= -0.6 and sentiment < -.2: #somewhat negative
                y["sentiment_label"] = "SOMEWHAT_NEGATIVE"
            elif sentiment >= -0.2 and sentiment < 0.2: #neutral
                y["sentiment_label"] = "NEUTRAL"
            elif sentiment >= 0.2 and sentiment < 0.6: #somewhat pos
                y["sentiment_label"] = "SOMEWHAT_POSITIVE"
            else:
                y["sentiment_label"] = "VERY_POSITIVE"

        #update sentiment_score = document sentiment & sentiment_label = enum
        y["sentiment_score"] = sentiment
    return input_data

class SpanTSA(nn.Module):
    def __init__(self, model_name="roberta-base", num_labels=5):
        super().__init__()
        self.encoder = RobertaModel.from_pretrained(model_name)
        hidden = self.encoder.config.hidden_size

        # span detection
        self.start_classifier = nn.Linear(hidden, 1)
        self.end_classifier = nn.Linear(hidden, 1)

        # sentiment classifier
        self.span_classifier = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden, num_labels)
        )

    def forward(self, input_ids,
                attention_mask,
                start_positions=None,
                end_positions=None,
                span_labels=None):
        outputs = self.encoder(input_ids=input_ids,
                               attention_mask=attention_mask)
        hidden_states = outputs.last_hidden_state  # (B, T, H)

        start_logits = self.start_classifier(hidden_states).squeeze(-1)
        end_logits = self.end_classifier(hidden_states).squeeze(-1)

        loss = 0

        if start_positions is not None:
            loss_fn = nn.BCEWithLogitsLoss()
            loss += loss_fn(start_logits, start_positions.float())
            loss += loss_fn(end_logits, end_positions.float())

        if span_labels is not None:
            span_loss = 0
            count = 0

            for b in range(len(span_labels)):
                for (s, e, label) in span_labels[b]:
                    span_repr = hidden_states[b, s:e+1].mean(dim=0)
                    logits = self.span_classifier(span_repr)

                    span_loss += nn.CrossEntropyLoss()(logits.unsqueeze(0),
                                                       torch.tensor([label],
                                                                    device=logits.device))
                    count += 1

            if count > 0:
                loss += span_loss / count

        return {
            "loss": loss,
            "start_logits": start_logits,
            "end_logits": end_logits,
        }