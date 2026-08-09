# Source Mapping & Evidence Identity — Wave 07

## Why these are separate
A source provider, a dataset/report family, an edited publication, a retrieval event and an individual parsed claim are not the same object.

W07 therefore freezes the hierarchy:

`SOURCE_SYSTEM -> SOURCE_RESOURCE -> PUBLICATION_VERSION -> RAW_CAPTURE -> SOURCE_OBSERVATION -> SOURCE_ENTITY_MAPPING -> CANONICAL_ENTITY`

This directly incorporates the Wave-06 finding that availability reports, rankings and official pages can be mutable/versioned.

## Source-system identity
Represents the owner/provider/system. It is not the endpoint, file or report edition.

## Source-resource identity
Represents an endpoint, dataset, report/page family or file family within a source system.

## Publication-version identity
Represents a distinct published or edited edition when that concept can be established. An availability report updated several times must not be flattened into one mutable row.

## Raw-capture identity
One retrieval event of exact bytes/payload. A repeated identical SHA-256 at a later retrieval time may legitimately have a different capture ID because retrieval time is evidence.

Required capture metadata includes source/resource identity, URI, retrieval time, raw SHA-256, immutable raw path and schema/contract version. Publication/first-known/effective/PIT fields are reserved here; W08 defines their exact eligibility semantics.

## Source-observation identity
Represents one parsed source claim/record and points to its raw capture.

## Source-entity mapping
A mapping record binds a source-scoped key to a canonical entity with:
- mapping method/state;
- evidence capture(s);
- resolution decision;
- scope/context;
- supersession history.

The durable source key is scoped by `source_system_id + entity_type + source_entity_key`. Names are labels/candidate evidence, not durable production keys.

## Derived/upstream sources
When a repository/API republishes or derives from another publisher, upstream provenance must be retained. Two wrappers around the same upstream data must not be counted as independent evidence.

## No overwrite rule
New publication versions, raw captures, observations and mapping decisions append. Later truth does not erase the evidence that a prior forecast actually had.
