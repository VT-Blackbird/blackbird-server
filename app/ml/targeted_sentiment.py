import json
import warnings
from typing import Any, Dict, List, Tuple

import nltk
import safetensors
import torch
from transformers import AutoTokenizer

from app.ml.utils import (
    SpanTSA,
    aggregate_document,
    classify_spans,
    decode_spans,
    update_label,
)
from app.schemas.search_response import SentimentScores

nltk.download('punkt_tab')
warnings.filterwarnings("ignore", message="`resume_download` is deprecated")

class Targeted_Sentiment():
    def __init__(self)->None:
        self.tsa_model, self.tokenizer= self.load_model()


    #load model
    def load_model(self)->Tuple[SpanTSA, AutoTokenizer]:
        model:SpanTSA = SpanTSA("roberta-base", num_labels=5)
        # Load state_dict using safetensors.torch.load_file for .safetensors format

        model.load_state_dict(
            safetensors.torch.load_file("app/ml/tsa_model_parameters/model.safetensors")
        )
        model.eval()

        # tokenizer = AutoTokenizer.from_pretrained("app/ml/tsa_model_parameters")
        tokenizer = AutoTokenizer.from_pretrained("roberta-base")
        return model, tokenizer

    #Uses model to make inference on sentiment for a single article
    def make_inference(
            self,
            text:str,
            threshold: float=0.5
        )->SentimentScores:
        sentences = nltk.sent_tokenize(text)

        all_targets = []

        for sent in sentences:
            encoding = self.tokenizer(sent, return_tensors="pt", truncation=True)

            with torch.no_grad():
                outputs = self.tsa_model.encoder(**encoding)
                hidden = outputs.last_hidden_state[0]

                start_logits = self.tsa_model.start_classifier(hidden).squeeze(-1)
                end_logits = self.tsa_model.end_classifier(hidden).squeeze(-1)

                spans = decode_spans(start_logits, end_logits)

                classified:List[Dict[str, Any]] = classify_spans(
                    self.tsa_model, hidden, spans)

                for c in classified:
                    c["text"] = self.tokenizer.decode(
                        encoding["input_ids"][0][c["start"]:c["end"] + 1]
                    )

                classified = sorted(classified,
                                    key=lambda x: x['confidence'], reverse=True)
                classified = [x for x in classified if x['confidence'] > threshold]
                all_targets.extend(classified)

        doc_score:float = aggregate_document(all_targets)
        del all_targets

        return SentimentScores(
            score = doc_score,
            label = update_label(doc_score)
        )

def load_data(path:str)->List[Dict[str, Any]] :
    with open(path, "r", encoding="utf-8") as f:
        data:List[Dict[str, Any]]= json.load(f)
        return data
