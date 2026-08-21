"""
Creates the tables used for entity resolution.

Current capabilities
--------------------
- entity_occurrences

Future capabilities
-------------------
- entities
- parcel_entity_roles
- association_evidence
- entity_associations
"""

import re
import pandas as pd


class EntityResolver:

    ############################################################
    # Initialization
    ############################################################

    def __init__(self):

        self.role_mapping = {

            "owner_name": {
                "role": "Owner",
                "address_column": "owner_address"
            },

            "owner_name_2": {
                "role": "Owner",
                "address_column": "owner_address"
            },

            "owner_care_of": {
                "role": "Owner Care Of",
                "address_column": "owner_address"
            },

            "taxpayer_name": {
                "role": "Taxpayer",
                "address_column": "taxpayer_address"
            },

            "taxpayer_care_of": {
                "role": "Taxpayer Care Of",
                "address_column": "taxpayer_address"
            },

            "tax_send_to_name": {
                "role": "Tax Send To",
                "address_column": "taxpayer_address"
            }

        }

        self.address_source_mapping = {

            "Owner": "owner_address",
            "Owner Care Of": "owner_address",

            "Taxpayer": "taxpayer_address",
            "Taxpayer Care Of": "taxpayer_address",
            "Tax Send To": "taxpayer_address"

        }

        self.organization_patterns = {

            r"\bLLC\b": ("LLC", "High"),
            r"\bL\.L\.C\b": ("LLC", "High"),

            r"\bINC\b": ("Corporation", "High"),
            r"\bINC\.\b": ("Corporation", "High"),
            r"\bCORP\b": ("Corporation", "High"),
            r"\bCORPORATION\b": ("Corporation", "High"),

            r"\bLP\b": ("Limited Partnership", "High"),
            r"\bLTD\b": ("Limited Company", "High"),

            r"\bBANK\b": ("Bank", "High"),

            r"\bTRUST\b": ("Trust", "Medium"),

            r"\bCHURCH\b": ("Church", "High"),

            r"\bCOUNTY\b": ("Government", "High"),
            r"\bCITY\b": ("Government", "High"),
            r"\bTOWNSHIP\b": ("Government", "High"),
            r"\bVILLAGE\b": ("Government", "High"),

            r"\bUNIVERSITY\b": ("University", "High"),

            r"\bFOUNDATION\b": ("Foundation", "High"),

            r"\bESTATE\b": ("Estate", "Medium"),
            r"\bESTATES\b": ("Estate", "Medium"),

            r"\bHOLDINGS\b": ("Holding Company", "Medium"),

            r"\bCOMPANY\b": ("Other Organization", "Medium"),
            r"\bCO\b": ("Other Organization", "Low")

        }

        self.organization_regex = "|".join(
            self.organization_patterns.keys()
        )

    ############################################################
    # Public Interface
    ############################################################

    def build(self, clean_df):
        """
        Runs the complete entity resolution pipeline.
        """

        entity_occurrences = self._create_entity_occurrences(clean_df)

        # Placeholder tables
        entities = pd.DataFrame()
        parcel_entity_roles = pd.DataFrame()
        association_evidence = pd.DataFrame()
        entity_associations = pd.DataFrame()

        return (
            entity_occurrences,
            entities,
            parcel_entity_roles,
            association_evidence,
            entity_associations
        )

    ############################################################
    # Stage 1 - Entity Occurrences
    ############################################################

    def _create_entity_occurrences(self, clean_df):

        entity_occurrences = self._extract_entity_occurrences(clean_df)

        entity_occurrences = self._classify_entity_type(
            entity_occurrences
        )

        entity_occurrences = self._classify_organizations(
            entity_occurrences
        )

        entity_occurrences = self._assign_address_source(
            entity_occurrences
        )

        entity_occurrences = self._assign_occurrence_ids(
            entity_occurrences
        )

        return entity_occurrences

    ############################################################

    def _extract_entity_occurrences(self, clean_df):

        tables = []

        for column, info in self.role_mapping.items():

            temp = clean_df[
                [
                    "parcel_number",
                    column,
                    info["address_column"]
                ]
            ].copy()

            temp.columns = [
                "parcel_number",
                "entity_name",
                "associated_address"
            ]

            temp["role"] = info["role"]

            tables.append(temp)

        entity_occurrences = pd.concat(
            tables,
            ignore_index=True
        )

        entity_occurrences = entity_occurrences[
            entity_occurrences["entity_name"] != ""
        ].copy()

        return entity_occurrences

    ############################################################

    def _classify_entity_type(self, entity_occurrences):

        entity_occurrences["entity_type"] = "Person"

        mask = entity_occurrences["entity_name"].str.contains(
            self.organization_regex,
            regex=True,
            case=False,
            na=False
        )

        entity_occurrences.loc[
            mask,
            "entity_type"
        ] = "Organization"

        return entity_occurrences

    ############################################################

    def _classify_organizations(self, entity_occurrences):

        mask = (
            entity_occurrences["entity_type"]
            == "Organization"
        )

        organization_info = (
            entity_occurrences.loc[
                mask,
                "entity_name"
            ]
            .apply(self._classify_organization)
        )

        entity_occurrences.loc[
            mask,
            "organization_type"
        ] = organization_info.str[0]

        entity_occurrences.loc[
            mask,
            "classification_confidence"
        ] = organization_info.str[1]

        return entity_occurrences

    ############################################################

    def _assign_address_source(self, entity_occurrences):

        entity_occurrences["address_source"] = (
            entity_occurrences["role"]
            .map(self.address_source_mapping)
        )

        return entity_occurrences

    ############################################################

    def _assign_occurrence_ids(self, entity_occurrences):

        entity_occurrences.insert(
            0,
            "occurrence_id",
            range(
                1,
                len(entity_occurrences) + 1
            )
        )

        return entity_occurrences

    ############################################################

    def _classify_organization(self, name):

        if name == "":
            return (None, None)

        for pattern, (org_type, confidence) in self.organization_patterns.items():

            if re.search(pattern, name):
                return (org_type, confidence)

        return ("Other Organization", "Low")

    ############################################################
    # Stage 2 - Canonical Entities
    ############################################################

    def _create_entities(self, entity_occurrences):
        raise NotImplementedError

    ############################################################
    # Stage 3 - Parcel Entity Roles
    ############################################################

    def _create_parcel_entity_roles(self,
                                    entity_occurrences,
                                    entities):
        raise NotImplementedError

    ############################################################
    # Stage 4 - Association Evidence
    ############################################################

    def _create_association_evidence(self,
                                     entity_occurrences,
                                     entities):
        raise NotImplementedError

    ############################################################
    # Stage 5 - Final Entity Associations
    ############################################################

    def _create_entity_associations(self,
                                    association_evidence):
        raise NotImplementedError