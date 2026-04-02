import json
from typing import Any, Dict, List

import nltk

# from safetensors.torch import safetensors
import safetensors
import torch
from transformers import RobertaTokenizer

from app.ml.utils import (
    SpanTSA,
    aggregate_document,
    classify_spans,
    decode_spans,
    save_json,
    update_document,
)

# nltk.download('punkt_tab')

#load model
def load_model():
    model:SpanTSA = SpanTSA("roberta-base", num_labels=5)
    # Load state_dict using safetensors.torch.load_file for .safetensors format

    model.load_state_dict(safetensors.torch.load_file("./tsa_model_parameters/model.safetensors"))
    model.eval()

    tokenizer = RobertaTokenizer.from_pretrained("./tsa_model_parameters")
    return model, tokenizer

def load_data(path:str)->List[Dict[str, Any]] :
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

#Uses model to make inference on sentiment for a single article
def make_inference(model, tokenizer, text, threshold=0.5)->Dict[str, Any]:
    sentences = nltk.sent_tokenize(text)

    all_targets = []

    for sent in sentences:
        encoding = tokenizer(sent, return_tensors="pt", truncation=True)

        with torch.no_grad():
            outputs = model.encoder(**encoding)
            hidden = outputs.last_hidden_state[0]

            start_logits = model.start_classifier(hidden).squeeze(-1)
            end_logits = model.end_classifier(hidden).squeeze(-1)

            spans = decode_spans(start_logits, end_logits)

            classified:List[Dict[str, Any]] = classify_spans(model, hidden, spans)

            for c in classified:
                c["text"] = tokenizer.decode(
                    encoding["input_ids"][0][c["start"]:c["end"] + 1]
                )

            classified = sorted(classified,
                                key=lambda x: x['confidence'], reverse=True)
            classified = [x for x in classified if x['confidence'] > threshold]
            all_targets.extend(classified)

    doc_score = aggregate_document(all_targets)

    return {
        "targets": all_targets,
        "document_sentiment": doc_score
    }

#applies sentiment model to all inputs
def run_model(path:str)->List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = load_data(path)
    model, tokenizer = load_model()

    output:List[Dict[str, Any]] = []
    for item in data:
        predicted:Dict[str, Any] = make_inference(model, tokenizer, item["content"])
        output.append(predicted)
    # update original dataset
    data = update_document(output, data, num_classes=5)
    save_json(data, f"updated_dataset{path}")
    #temp save all output data from model, testing purposes
    output_path = f"output_{path}"
    save_json(output, output_path)

if __name__ == "__main__":
    run_model("test_sentiment.json")