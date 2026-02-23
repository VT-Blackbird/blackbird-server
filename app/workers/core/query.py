from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

@dataclass(init=True, repr=True, eq=True)
#==========================================
# Query: Represents a scraping query with all necessary parameters and metadata
# Contains fields for query text and status tracking
#==========================================

class Query:
    text: str

    #Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # last_run: datetime | None = None
    # run_count: int = 0
    #
    # #currently not called anywhere, useful for tracking later on w/ saving searches
    # def mark_run(self):
    #     #updates execution metadata after a run
    #     self.last_run = datetime.now(timezone.utc) #store in UTC
    #     self.run_count += 1
    