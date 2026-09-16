from pydantic import BaseModel


# ==========================================================
# ENTITY SEARCH SCHEMAS
# ==========================================================

class EntitySearchResult(BaseModel):
    """
    One resolved entity returned by an entity search.
    """

    entity_id: int
    canonical_name: str
    entity_type: str
    canonical_address: str | None = None
    organization_type: str | None = None
    organization_classification_confidence: str | None = None
    occurrence_count: int


class EntitySearchResponse(BaseModel):
    """
    Complete response returned by the entity-search endpoint.
    """

    query: str
    result_count: int
    results: list[EntitySearchResult]


# ==========================================================
# ENTITY DETAIL SCHEMA
# ==========================================================

class EntityDetailResponse(BaseModel):
    """
    Detailed information about one resolved entity.
    """

    entity_id: int
    canonical_name: str
    entity_type: str
    canonical_address: str | None = None
    organization_type: str | None = None
    organization_classification_confidence: str | None = None
    occurrence_count: int


# ==========================================================
# ENTITY PARCEL SCHEMAS
# ==========================================================

class EntityParcelResult(BaseModel):
    """
    One parcel directly associated with an entity.
    """

    parcel_number: str
    property_address: str | None = None
    roles: list[str]

    principal_residence_exemption_percentage: int
    property_class: str | None = None

    tax_value: int
    assessed_value: int
    state_equalized_value: int


class EntityParcelsResponse(BaseModel):
    """
    Parcels directly associated with one resolved entity.
    """

    entity_id: int
    parcel_count: int
    parcels: list[EntityParcelResult]


# ==========================================================
# ENTITY ASSOCIATION SCHEMAS
# ==========================================================

class EntityAssociationResult(BaseModel):
    """
    One entity associated with the searched entity.
    """

    association_id: int

    associated_entity_id: int
    associated_canonical_name: str
    associated_entity_type: str
    associated_canonical_address: str | None = None

    associated_organization_type: str | None = None
    associated_organization_classification_confidence: str | None = None

    association_confidence: str
    evidence_count: int
    evidence_rule_count: int


class EntityAssociationsResponse(BaseModel):
    """
    Associations for one resolved entity.
    """

    entity_id: int
    association_count: int
    associations: list[EntityAssociationResult]


# ==========================================================
# ASSOCIATION EVIDENCE SCHEMAS
# ==========================================================

class AssociationEntitySummary(BaseModel):
    """
    Basic identifying information for one side of an
    entity association.
    """

    entity_id: int
    canonical_name: str
    entity_type: str


class AssociationEvidenceResult(BaseModel):
    """
    One piece of evidence supporting an entity association.
    """

    evidence_id: int
    evidence_rule: str
    evidence_strength: str

    parcel_number_a: str | None = None
    parcel_number_b: str | None = None

    role_a: str
    role_b: str

    shared_address: str | None = None
    address_type: str | None = None


class AssociationEvidenceResponse(BaseModel):
    """
    Complete evidence record for one entity association.
    """

    association_id: int

    entity_a: AssociationEntitySummary
    entity_b: AssociationEntitySummary

    association_confidence: str
    evidence_count: int
    evidence_rule_count: int

    evidence: list[AssociationEvidenceResult]