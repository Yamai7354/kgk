---
description: Validate KGK kernel consistency and module contracts
agent: kgk-architect
---
Run a consistency check across KGK modules:

1. Verify all `__init__.py` re-exports match module contents
2. Check that `GraphStore` Protocol is implemented correctly by `InMemoryGraphStore`
3. Verify `kernel.py` wires all modules without circular imports
4. Ensure all `Statement` mutations use `model_copy(update={...})`
5. Confirm `ProvenanceTracker` is called in all mutation paths

Command:
```bash
python -c "
from kernel import KnowledgeGraphKernel
from graph import GraphStore, InMemoryGraphStore
from models import Statement, StatementStatus
from provenance import ProvenanceTracker

# Verify imports and protocol compliance
kgk = KnowledgeGraphKernel()
assert isinstance(kgk.store, InMemoryGraphStore)
assert isinstance(kgk.provenance, ProvenanceTracker)

# Verify statement mutation pattern
import inspect
source = inspect.getsource(kgk.retraction.retract)
assert 'model_copy' in source, 'RetractionService must use model_copy'

# Verify provenance tracking
from models import EntityCreate, RelationCreate, StatementCreate
result = kgk.ingest(StatementCreate(
    subject=EntityCreate(label='Validate'),
    relation=RelationCreate(label='test'),
    object=EntityCreate(label='check'),
    provenance=__import__('provenance').ProvenanceRecord(source='validate')
))
lineage = kgk.provenance.lineage_for(result.statement.id)
assert len(lineage) >= 1
print('All KGK consistency checks passed.')
"
```
