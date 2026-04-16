from typing import Any, Dict, List, Protocol, Tuple

import nltk
from pysentimiento import create_analyzer

nltk.download('punkt_tab')

class SentimentPrediction(Protocol):
    output:str
    probas:Dict[str, float]
class NewsSentiment():
    def __init__(self) -> None:
        self.tsc = self.load_targeting_model()

    def make_inference(
            self,
            text: str,
            threshold: float = 0.5,
    ) -> Tuple[str, float]:

        all_sentiment: List[float] = []
        sentences = nltk.sent_tokenize(text)

        for sent in sentences:
            pred: SentimentPrediction = self.get_overall_sentiment(sent)

            # confidence = max probability
            confidence = max(pred.probas.values())

            if confidence >= threshold:
                label_map = {"NEG": -1.0, "NEU": 0.0, "POS": 1.0}
                bin = label_map.get(pred.output, 0.0)
                score:float = pred.probas[pred.output]*bin or -2.0
                all_sentiment.append(score)

        if not all_sentiment:
            return ("NA", -2.0)

        doc_score: float = sum(all_sentiment) / len(all_sentiment)

        label:str = self.update_label(doc_score)
        print(f"\nSentiment: {all_sentiment}, label: {label}, score: {doc_score}")
        return (label, doc_score)

    def update_label(
            self,
            sentiment: float,
            num_classes: int = 5
    ) -> str:
        if sentiment == -2.0:
            return "NA"
        if sentiment is not None and (sentiment > 1 or sentiment < -1):
            return "NA"
        if num_classes == 3:
            if sentiment < -0.33:
                return "NEGATIVE"
            elif sentiment >= 0.3:
                return "POSITIVE"
            else:
                return "NEUTRAL"
        else:
            if sentiment < -0.6:
                return "VERY_NEGATIVE"
            elif sentiment < -0.2:
                return "SOMEWHAT_NEGATIVE"
            elif sentiment < 0.2:
                return "NEUTRAL"
            elif sentiment < 0.6:
                return "SOMEWHAT_POSITIVE"
            else:
                return "VERY_POSITIVE"


    def load_targeting_model(self)-> Any:
        tsc_model = create_analyzer(task = "sentiment", lang = "en")
        return tsc_model



    def get_overall_sentiment(self,
                              text:str)->SentimentPrediction:
      return self.tsc.predict(text)