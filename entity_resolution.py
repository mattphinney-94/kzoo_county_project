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

            # ----------------------------------------------------------
            # Legal entity indicators
            # ----------------------------------------------------------

            r"\bLLC\b": ("LLC", "High"),
            r"\bL\.L\.C\b": ("LLC", "High"),

            r"\bPLLC\b": ("LLC", "High"),

            r"\bINC\b": ("Corporation", "High"),
            r"\bINC\.\b": ("Corporation", "High"),
            r"\bINCORPORATED\b": ("Corporation", "High"),

            r"\bCORP\b": ("Corporation", "High"),
            r"\bCORPORATION\b": ("Corporation", "High"),

            r"\bLP\b": ("Limited Partnership", "High"),
            r"\bLLP\b": ("Limited Partnership", "High"),
            r"\bLTD\b": ("Limited Company", "High"),

            r"\bPARTNERSHIP\b": ("Partnership", "High"),

            # ----------------------------------------------------------
            # Financial institutions
            # ----------------------------------------------------------

            r"\bBANK\b": ("Bank", "High"),
            r"\bCREDIT UNION\b": ("Financial Institution", "High"),
            r"\bMORTGAGE\b": ("Financial Institution", "Medium"),

            # ----------------------------------------------------------
            # Trusts and estates
            # ----------------------------------------------------------

            r"\bTRUST\b": ("Trust", "Medium"),
            r"\bTRST\b": ("Trust", "Medium"),

            r"\bESTATE\b": ("Estate", "Medium"),
            r"\bESTATES\b": ("Estate", "Medium"),

            # ----------------------------------------------------------
            # Religious organizations
            # ----------------------------------------------------------

            r"\bCHURCH\b": ("Church", "High"),
            r"\bCOGIC\b": ("Church", "High"),

            r"\bCONGREGATION\b": ("Religious Organization", "High"),
            r"\bMINISTRY\b": ("Religious Organization", "Medium"),
            r"\bMINISTRIES\b": ("Religious Organization", "Medium"),

            r"\bCHAPEL\b": ("Religious Organization", "Medium"),
            r"\bTEMPLE\b": ("Religious Organization", "Medium"),

            # ----------------------------------------------------------
            # Government
            # ----------------------------------------------------------

            r"\bCOUNTY\b": ("Government", "High"),
            r"\bCITY\b": ("Government", "High"),
            r"\bTOWNSHIP\b": ("Government", "High"),
            r"\bVILLAGE\b": ("Government", "High"),

            r"\bDEPARTMENT\b": ("Government", "Medium"),
            r"\bDEPT\b": ("Government", "Medium"),

            r"\bAUTHORITY\b": ("Government", "Medium"),

            # ----------------------------------------------------------
            # Educational organizations
            # ----------------------------------------------------------

            r"\bUNIVERSITY\b": ("University", "High"),
            r"\bCOLLEGE\b": ("Educational Organization", "High"),
            r"\bSCHOOL\b": ("Educational Organization", "Medium"),
            r"\bACADEMY\b": ("Educational Organization", "Medium"),

            # ----------------------------------------------------------
            # Nonprofit / institutional organizations
            # ----------------------------------------------------------

            r"\bFOUNDATION\b": ("Foundation", "High"),

            r"\bASSOCIATION\b": ("Other Organization", "Medium"),

            # ----------------------------------------------------------
            # Business-name indicators
            # ----------------------------------------------------------

            r"\bPROPERTY\b": ("Other Organization", "Medium"),
            r"\bPROPERTIES\b": ("Other Organization", "Medium"),

            r"\bREALTY\b": ("Other Organization", "Medium"),
            r"\bREAL ESTATE\b": ("Other Organization", "Medium"),

            r"\bRENTAL\b": ("Other Organization", "Medium"),
            r"\bRENTALS\b": ("Other Organization", "Medium"),

            r"\bDEVELOPMENT\b": ("Other Organization", "Medium"),

            r"\bCONSTRUCTION\b": ("Other Organization", "Medium"),

            r"\bMANAGEMENT\b": ("Other Organization", "Medium"),

            r"\bINVESTMENT\b": ("Other Organization", "Medium"),
            r"\bINVESTMENTS\b": ("Other Organization", "Medium"),

            r"\bENTERPRISE\b": ("Other Organization", "Medium"),
            r"\bENTERPRISES\b": ("Other Organization", "Medium"),

            r"\bSERVICES\b": ("Other Organization", "Medium"),

            r"\bSOLUTIONS\b": ("Other Organization", "Medium"),

            r"\bCOMMUNITIES\b": ("Other Organization", "Medium"),

            r"\bGROUP\b": ("Other Organization", "Medium"),

            r"\bHOLDINGS\b": ("Holding Company", "Medium"),

            r"\bCOMPANY\b": ("Other Organization", "Medium"),
            r"\bCO\b": ("Other Organization", "Low"),

            r"\bSALES\b": ("Other Organization", "Medium"),

            r"\bINN\b": ("Other Organization", "Medium"),

            r"\bOUTFITTER\b": ("Other Organization", "Medium"),
            r"\bOUTFITTERS\b": ("Other Organization", "Medium"),

            r"\bNAVIGATORS\b": ("Other Organization", "Medium"),

            r"\bREVITALIZATION\b": ("Other Organization", "Medium")
        }

        # This is used to classify specific troublesome entities that aren't
        # handled correctly by the entity resolution algorithm.
        self.entity_type_overrides = {
            "CASH N A FLASH": "Organization",
            "MICHIGAN FAST CASH FLIP": "Organization",
            "HOPE THRU NAVIGATION": "Organization",
            "PAYMENT IN LIEU OF TAXES": "Unknown"
        }

        self.entity_name_replacements = {
            "CORP": "CORPORATION",
            "INC": "INCORPORATED",
            "CO": "COMPANY"
        }

        self.organization_regex = "|".join(
            self.organization_patterns.keys()
        )

    ############################################################
    # Public Interface
    ############################################################

    # Runs the complete entity resolution pipeline.
    def build(self, clean_df):

        # Stage 1
        # Extract every entity occurrence from the source data.
        entity_occurrences = self._create_entity_occurrences(
            clean_df
        )

        # Stage 2
        # Create unique raw entities before making resolution decisions.
        raw_entities = self._create_raw_entities(
            entity_occurrences
        )

        # Stage 3
        # Resolve raw entities into consolidated entities.
        resolved_entities = self._merge_entities(
            raw_entities
        )

        # Finalize resolved entities and obtain the mapping between
        # source occurrences and final entity IDs.
        (
            entities,
            occurrence_to_entity
        ) = self._finalize_entities(
            resolved_entities
        )

        # Attach the final entity ID to every source occurrence.
        entity_occurrences["entity_id"] = (
            entity_occurrences["occurrence_id"]
            .map(occurrence_to_entity)
        )

        # Every occurrence should resolve to exactly one entity.
        if entity_occurrences["entity_id"].isna().any():
            unresolved = entity_occurrences.loc[
                entity_occurrences["entity_id"].isna(),
                "occurrence_id"
            ].tolist()

            raise ValueError(
                "Some entity occurrences were not assigned to an "
                f"entity: {unresolved[:10]}"
            )

        entity_occurrences["entity_id"] = (
            entity_occurrences["entity_id"]
            .astype(int)
        )

        # Later stages
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
    # Stage 1
    # Entity Occurrences
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

        entity_occurrences = (
            entity_occurrences.copy()
        )

        # Default classification for the current version.
        entity_occurrences[
            "entity_type"
        ] = "Person"

        # ----------------------------------------------------------
        # Organization-pattern classification
        # ----------------------------------------------------------

        organization_mask = (
            entity_occurrences[
                "entity_name"
            ]
            .str.contains(
                self.organization_regex,
                regex=True,
                case=False,
                na=False
            )
        )

        entity_occurrences.loc[
            organization_mask,
            "entity_type"
        ] = "Organization"

        # ----------------------------------------------------------
        # Explicit overrides
        # ----------------------------------------------------------

        overrides = (
            entity_occurrences[
                "entity_name"
            ]
            .map(
                self.entity_type_overrides
            )
        )

        override_mask = (
            overrides.notna()
        )

        entity_occurrences.loc[
            override_mask,
            "entity_type"
        ] = overrides.loc[
            override_mask
        ]

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
            "organization_classification_confidence"
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
    # Stage 2
    # Raw Entities
    ############################################################

    def _create_raw_entities(self, entity_occurrences):
        """
        Create one raw entity for each unique combination of:

            entity_name
            entity_type
            associated_address

        Final entity IDs are not assigned until entity resolution
        has been completed.

        _occurrence_ids is an internal provenance field used to track
        which source occurrences belong to each resolved entity.
        """

        raw_entities = (
            entity_occurrences
            .groupby(
                [
                    "entity_name",
                    "entity_type",
                    "associated_address"
                ],
                dropna=False,
                sort=False
            )
            .agg(
                organization_type=(
                    "organization_type",
                    "first"
                ),
                organization_classification_confidence=(
                    "organization_classification_confidence",
                    self._highest_confidence
                ),
                occurrence_count=(
                    "occurrence_id",
                    "size"
                ),
                _occurrence_ids=(
                    "occurrence_id",
                    lambda x: tuple(x)
                )
            )
            .reset_index()
        )

        raw_entities = raw_entities.rename(
            columns={
                "entity_name": "canonical_name",
                "associated_address": "canonical_address"
            }
        )

        return raw_entities

    ############################################################
    # Stage 3
    # Entity Resolution
    ############################################################

    # ----------------------------------------------------------
    # Resolution Engine
    # ----------------------------------------------------------

    # Create the merge engine
    def _merge_entities(self, entities):
        """
        Repeatedly apply entity-resolution rules until a complete pass
        results in no additional entity merges.
        """

        entities = entities.copy()

        while True:

            count_before = len(entities)

            # Contextual matching
            entities = self._merge_blank_addresses(
                entities
            )

            entities = self._merge_middle_initial_variants(
                entities
            )

            entities = self._merge_suffix_variants(
                entities
            )

            # Transformation-based matching
            entities = self._merge_on_match_key(
                entities,
                self._expand_common_abbreviations
            )

            count_after = len(entities)

            if count_after == count_before:
                break

        return entities.reset_index(drop=True)

    # ----------------------------------------------------------
    # Resolution Rules
    # ----------------------------------------------------------

    def _merge_blank_addresses(self, entities):
        """
        Merge an entity with a blank address into a same-named entity
        only when exactly one distinct nonblank address exists for that
        name and entity type.

        Ambiguous names with multiple known addresses are left unresolved.
        """

        entities = entities.copy()

        known_addresses = (
            entities[
                entities["canonical_address"] != ""
                ]
            .groupby(
                ["entity_type", "canonical_name"]
            )["canonical_address"]
            .agg(lambda x: sorted(set(x)))
        )

        # Keep only names for which exactly one known address exists
        unique_address_lookup = {
            key: addresses[0]
            for key, addresses in known_addresses.items()
            if len(addresses) == 1
        }

        blank_mask = entities["canonical_address"] == ""

        for index in entities.index[blank_mask]:

            key = (
                entities.at[index, "entity_type"],
                entities.at[index, "canonical_name"]
            )

            if key in unique_address_lookup:
                entities.at[
                    index,
                    "canonical_address"
                ] = unique_address_lookup[key]

        # Blank-address rows that received an address can now collapse
        # with the corresponding known-address entity.
        entities = self._merge_on_key(
            entities,
            [
                "entity_type",
                "canonical_name",
                "canonical_address"
            ]
        )

        return entities

    def _merge_middle_initial_variants(self, entities):
        """
        Merge person entities that differ only in middle-name detail when
        the surrounding context makes the match unambiguous.

        Requirements:
            - Both entities must be classified as Person.
            - Both must have the same nonblank canonical address.
            - Last name must match.
            - First name must match.
            - Suffix must match.
            - Middle-name variants must be mutually compatible.

        Examples that can merge:
            YOUNG, CAVEL
            YOUNG, CAVEL J

            SMITH, JOHN A
            SMITH, JOHN ALAN

            SMITH, JOHN
            SMITH, JOHN A
            SMITH, JOHN ALAN

        Example that will NOT merge:
            SMITH, JOHN
            SMITH, JOHN A
            SMITH, JOHN B

        because A and B provide conflicting identifying information.
        """

        entities = entities.copy().reset_index(drop=True)

        candidate_rows = []

        for index, row in entities.iterrows():

            # Only apply this rule to people.
            if row["entity_type"] != "Person":
                continue

            address = row["canonical_address"]

            # Do not use unresolved blank addresses for contextual matching.
            if pd.isna(address) or str(address).strip() == "":
                continue

            parsed = self._parse_person_name(
                row["canonical_name"]
            )

            if parsed is None:
                continue

            candidate_rows.append({
                "row_index": index,
                "canonical_address": address,
                "last_name": parsed["last_name"],
                "first_name": parsed["first_name"],
                "middle_tokens": parsed["middle_tokens"],
                "suffix": parsed["suffix"]
            })

        if not candidate_rows:
            return entities

        candidates = pd.DataFrame(candidate_rows)

        groups_to_merge = []

        group_columns = [
            "canonical_address",
            "last_name",
            "first_name",
            "suffix"
        ]

        for _, group in candidates.groupby(
                group_columns,
                dropna=False,
                sort=False
        ):

            if len(group) < 2:
                continue

            middle_variants = list(
                dict.fromkeys(
                    group["middle_tokens"].tolist()
                )
            )

            # If all middle-name representations are already identical,
            # this rule has nothing to resolve.
            if len(middle_variants) < 2:
                continue

            nonblank_variants = [
                variant
                for variant in middle_variants
                if len(variant) > 0
            ]

            # No middle information at all.
            if not nonblank_variants:
                continue

            # Every known middle-name variant must be compatible with
            # every other known variant.
            compatible = True

            for i in range(len(nonblank_variants)):
                for j in range(i + 1, len(nonblank_variants)):

                    if not self._middle_tokens_compatible(
                            nonblank_variants[i],
                            nonblank_variants[j]
                    ):
                        compatible = False
                        break

                if not compatible:
                    break

            if compatible:
                groups_to_merge.append(
                    group["row_index"].tolist()
                )

        return self._collapse_index_groups(
            entities,
            groups_to_merge
        )

    def _merge_suffix_variants(self, entities):
        """
        Merge person entities that differ only because one record contains
        a suffix and another does not, but only when there is exactly one
        nonblank suffix represented in the candidate group.

        Requirements:
            - Entity must be a Person.
            - Address must be identical and nonblank.
            - First, last, and middle names must match.
            - There must not be conflicting suffixes.

        Example that can merge:
            SMITH, JOHN
            SMITH, JOHN JR

        Example that will NOT merge:
            SMITH, JOHN
            SMITH, JOHN JR
            SMITH, JOHN SR

        because the suffix-free record is ambiguous.
        """

        entities = entities.copy().reset_index(drop=True)

        candidate_rows = []

        for index, row in entities.iterrows():

            if row["entity_type"] != "Person":
                continue

            address = row["canonical_address"]

            if pd.isna(address) or str(address).strip() == "":
                continue

            parsed = self._parse_person_name(
                row["canonical_name"]
            )

            if parsed is None:
                continue

            candidate_rows.append({
                "row_index": index,
                "canonical_address": address,
                "last_name": parsed["last_name"],
                "first_name": parsed["first_name"],
                "middle_tokens": parsed["middle_tokens"],
                "suffix": parsed["suffix"]
            })

        if not candidate_rows:
            return entities

        candidates = pd.DataFrame(candidate_rows)

        groups_to_merge = []

        group_columns = [
            "canonical_address",
            "last_name",
            "first_name",
            "middle_tokens"
        ]

        for _, group in candidates.groupby(
                group_columns,
                dropna=False,
                sort=False
        ):

            if len(group) < 2:
                continue

            suffixes = set(
                group["suffix"].tolist()
            )

            nonblank_suffixes = {
                suffix
                for suffix in suffixes
                if suffix != ""
            }

            # No suffix information exists, so this isn't a suffix
            # variation.
            if not nonblank_suffixes:
                continue

            # More than one suffix means the group is ambiguous.
            #
            # For example:
            # JOHN SMITH
            # JOHN SMITH JR
            # JOHN SMITH SR
            if len(nonblank_suffixes) > 1:
                continue

            groups_to_merge.append(
                group["row_index"].tolist()
            )

        return self._collapse_index_groups(
            entities,
            groups_to_merge
        )

    # ----------------------------------------------------------
    # Resolution Infrastructure
    # ----------------------------------------------------------

    def _merge_on_match_key(self, entities, transform_function):
        """
        Apply a name transformation to create a temporary matching key,
        then merge entities with the same:

        entity_type
        match_name
        canonical_address

        The temporary match_name is removed afterward.
        """

        entities = entities.copy()

        entities["match_name"] = (
            entities["canonical_name"]
            .apply(transform_function)
        )

        entities = self._merge_on_key(
            entities,
            [
                "entity_type",
                "match_name",
                "canonical_address"
            ]
        )

        entities = entities.drop(
            columns="match_name",
            errors="ignore"
        )

        return entities

    def _merge_on_key(self, entities, grouping_columns):
        """
        Repeatedly merge entities sharing the same grouping key until
        another pass produces no additional merges.

        Parameters
        ----------
        entities : pandas.DataFrame
            Current entity table.

        grouping_columns : list[str]
            Columns defining which rows are eligible to merge.

        Returns
        -------
        pandas.DataFrame
            Entity table after the merge rule reaches a stable state.
        """

        entities = entities.copy()

        while True:

            count_before = len(entities)

            merged_rows = []

            for _, group in entities.groupby(
                    grouping_columns,
                    dropna=False,
                    sort=False
            ):
                merged_rows.append(
                    self._merge_group(group)
                )

            entities = pd.DataFrame(merged_rows)

            count_after = len(entities)

            # Stop once another pass causes no additional merges
            if count_after == count_before:
                break

        return entities.reset_index(drop=True)

    """
    Merge a group of duplicate entities into one entity.
    """
    def _merge_group(self, group):

        row = {}

        # Canonical name
        row["canonical_name"] = max(
            group["canonical_name"],
            key=self._name_score
        )

        # Match name
        if "match_name" in group.columns:
            row["match_name"] = group["match_name"].iloc[0]

        # Entity type
        row["entity_type"] = (
            group["entity_type"]
            .mode()
            .iat[0]
        )

        # Canonical address
        addresses = (
            group["canonical_address"]
            .replace("", pd.NA)
            .dropna()
        )

        if len(addresses):

            row["canonical_address"] = (
                addresses
                .value_counts()
                .idxmax()
            )

        else:

            row["canonical_address"] = ""

        # Organization type
        org_types = (
            group["organization_type"]
            .dropna()
        )

        row["organization_type"] = (
            org_types.iloc[0]
            if len(org_types)
            else None
        )

        # Classification confidence
        row["organization_classification_confidence"] = (
            self._highest_confidence(
                group["organization_classification_confidence"]
            )
        )

        # Occurrence count
        row["occurrence_count"] = (
            group["occurrence_count"]
            .sum()
        )

        # Source occurrences
        if "_occurrence_ids" in group.columns:
            row["_occurrence_ids"] = tuple(
                occurrence_id
                for occurrence_ids in group["_occurrence_ids"]
                for occurrence_id in occurrence_ids
            )

        return row

    def _collapse_index_groups(
            self,
            entities,
            groups_to_merge
    ):
        """
        Collapse explicitly approved groups of entity rows.

        Each item in groups_to_merge should be a list of DataFrame
        row indexes that have already been determined to represent
        the same entity.
        """

        entities = entities.copy().reset_index(drop=True)

        replacements = {}
        consumed_indexes = set()

        for indexes in groups_to_merge:

            indexes = list(
                dict.fromkeys(indexes)
            )

            if len(indexes) < 2:
                continue

            # A row should never belong to two independent merge groups
            # during the same resolution rule.
            overlap = (
                    set(indexes)
                    & consumed_indexes
            )

            if overlap:
                raise ValueError(
                    "An entity was assigned to more than one "
                    "merge group."
                )

            group = entities.loc[indexes]

            merged_row = self._merge_group(
                group
            )

            # Keep the merged entity in the position of the first
            # member of the group.
            anchor_index = indexes[0]

            replacements[anchor_index] = (
                merged_row
            )

            consumed_indexes.update(
                indexes[1:]
            )

        output_rows = []

        for index, row in entities.iterrows():

            if index in consumed_indexes:
                continue

            if index in replacements:
                output_rows.append(
                    replacements[index]
                )

            else:
                output_rows.append(
                    row.to_dict()
                )

        result = pd.DataFrame(output_rows)

        # Preserve the original schema and column order.
        for column in entities.columns:

            if column not in result.columns:
                result[column] = None

        result = result[
            entities.columns
        ]

        return result.reset_index(drop=True)

    # ----------------------------------------------------------
    # Matching Transformations
    # ----------------------------------------------------------

    def _normalize_match_name(self, name):
        """
        Perform lightweight normalization used only for matching.

        This does not change the canonical name stored in the final
        entities table.
        """

        if pd.isna(name):
            return ""

        name = str(name).upper().strip()

        # Remove periods
        name = name.replace(".", "")

        # Collapse repeated whitespace
        name = re.sub(r"\s+", " ", name)

        # Standardize spacing around commas
        name = re.sub(r"\s*,\s*", ", ", name)

        # Remove repeated commas
        name = re.sub(r",+", ",", name)

        # Remove leading/trailing whitespace and commas
        name = name.strip(" ,")

        # Remove status annotations used in source names
        name = re.sub(
            r"\s*\(?\bDECEASED\b\)?\s*$",
            "",
            name
        ).strip()

        return name

    def _expand_common_abbreviations(self, name):
        """
        Expand known entity-name abbreviations for matching.

        Replacements are applied only to complete words so that substrings
        inside other words are not accidentally changed.
        """

        name = self._normalize_match_name(name)

        for old, new in self.entity_name_replacements.items():
            name = re.sub(
                rf"\b{re.escape(old)}\b",
                new,
                name
            )

        # Collapse whitespace again in case a replacement introduced it.
        name = re.sub(r"\s+", " ", name).strip()

        return name

    # ----------------------------------------------------------
    # Matching Helpers
    # ----------------------------------------------------------

    def _parse_person_name(self, name):
        """
        Parse a plausible individual person's name into:

            last_name
            first_name
            middle_tokens
            suffix

        Supported formats include:

            SMITH, JOHN
            SMITH, JOHN A
            SMITH, JOHN ALAN
            SMITH, JOHN A JR
            SMITH, JOHN ALAN, JR
            SMITH JR, JOHN A

            SMITH JOHN
            SMITH JOHN A
            SMITH JOHN ALAN
            SMITH JOHN A JR

        The parser is intentionally conservative. Names with joint-owner
        markers, ambiguous comma structures, unresolved annotations, or
        other structures that cannot be interpreted safely return None.
        """

        name = self._normalize_match_name(name)

        if not name:
            return None

        # ----------------------------------------------------------
        # Reject joint / compound ownership records
        # ----------------------------------------------------------

        if (
                "&" in name
                or "/" in name
                or re.search(
            r"\b(?:AND|ET AL|ET UX)\b",
            name
        )
        ):
            return None

        # Any parenthetical annotation remaining after match-name
        # normalization is considered too ambiguous to parse safely.
        #
        # For example, (DECEASED) should already have been removed by
        # _normalize_match_name().
        if "(" in name or ")" in name:
            return None

        # ----------------------------------------------------------
        # Suffix definitions
        # ----------------------------------------------------------

        suffix_map = {
            "JR": "JR",
            "JUNIOR": "JR",
            "SR": "SR",
            "SENIOR": "SR",
            "II": "II",
            "III": "III",
            "IV": "IV"
        }

        suffix = ""

        # ----------------------------------------------------------
        # Comma format
        #
        # LAST, FIRST MIDDLE
        # LAST, FIRST MIDDLE, JR
        # LAST JR, FIRST MIDDLE
        # ----------------------------------------------------------

        if "," in name:

            parts = [
                part.strip()
                for part in name.split(",")
                if part.strip()
            ]

            if len(parts) < 2:
                return None

            # More than two comma-separated pieces are allowed only
            # when the final piece is a recognized suffix.
            #
            # BROWN, ROBERT WENDELL, JR
            #
            # is safe.
            #
            # KALE, ANDRIJA-WALDBILLIG, ZORICA
            #
            # is structurally ambiguous and is not parsed.
            if len(parts) > 2:

                if len(parts) != 3:
                    return None

                trailing_suffix = suffix_map.get(
                    parts[2]
                )

                if trailing_suffix is None:
                    return None

                suffix = trailing_suffix

            last_tokens = parts[0].split()
            given_tokens = parts[1].split()

            if not last_tokens or not given_tokens:
                return None

            # ------------------------------------------------------
            # Suffix attached to last-name portion
            #
            # DERRING III, ALBERT
            # JONES JR, JIMMIE LEE
            # ------------------------------------------------------

            last_suffix = suffix_map.get(
                last_tokens[-1]
            )

            if last_suffix is not None:

                if suffix and suffix != last_suffix:
                    return None

                suffix = last_suffix

                last_tokens = last_tokens[:-1]

                if not last_tokens:
                    return None

            # ------------------------------------------------------
            # Suffix attached to given-name portion
            #
            # SMITH, JOHN A JR
            # ------------------------------------------------------

            given_suffix = suffix_map.get(
                given_tokens[-1]
            )

            if given_suffix is not None:

                if suffix and suffix != given_suffix:
                    return None

                suffix = given_suffix

                given_tokens = given_tokens[:-1]

                if not given_tokens:
                    return None


        # ----------------------------------------------------------
        # No-comma format
        #
        # LAST FIRST MIDDLE SUFFIX
        # ----------------------------------------------------------

        else:

            tokens = name.split()

            if len(tokens) < 2:
                return None

            # Be conservative with very long no-comma names.
            # They may represent organizations, multiple people, or
            # structures whose ordering cannot be inferred reliably.
            if len(tokens) > 5:
                return None

            # ------------------------------------------------------
            # Terminal suffix
            #
            # MINER MICHAEL C JR
            # ------------------------------------------------------

            terminal_suffix = suffix_map.get(
                tokens[-1]
            )

            if terminal_suffix is not None:
                suffix = terminal_suffix
                tokens = tokens[:-1]

            if len(tokens) < 2:
                return None

            # ------------------------------------------------------
            # Avoid guessing at compound surnames
            # ------------------------------------------------------

            surname_particles = {
                "DA",
                "DE",
                "DEL",
                "DI",
                "DOS",
                "LA",
                "VAN",
                "VON"
            }

            if tokens[0] in surname_particles:
                return None

            # A one-letter apparent first name in a no-comma record is
            # particularly difficult to interpret.
            #
            # Example:
            #     MOHAMMED S RIAZ
            #
            # Rather than assuming S is the first name and RIAZ is a
            # middle name, leave the record unresolved.
            if (
                    len(tokens) > 2
                    and len(tokens[1]) == 1
            ):
                return None

            # County data commonly uses:
            #
            # LAST FIRST [MIDDLE...]
            #
            last_tokens = [tokens[0]]
            given_tokens = tokens[1:]

        # ----------------------------------------------------------
        # Final validation
        # ----------------------------------------------------------

        if not last_tokens or not given_tokens:
            return None

        last_name = " ".join(
            last_tokens
        )

        first_name = given_tokens[0]

        middle_tokens = tuple(
            given_tokens[1:]
        )

        if not last_name or not first_name:
            return None

        return {
            "last_name": last_name,
            "first_name": first_name,
            "middle_tokens": middle_tokens,
            "suffix": suffix
        }

    def _middle_tokens_compatible(self, left, right):
        """
        Determine whether two nonblank middle-name representations are
        compatible.

        Compatible examples:
            ("A",)       and ("ALAN",)
            ("ALAN",)    and ("A",)
            ("A", "B")   and ("ALAN", "BETH")
            ("ALAN",)    and ("ALAN",)

        Incompatible examples:
            ("A",)       and ("B",)
            ("ALAN",)    and ("ANDREW",)
            ("A", "B")   and ("A",)
        """

        if len(left) != len(right):
            return False

        for left_token, right_token in zip(
                left,
                right
        ):

            if left_token == right_token:
                continue

            # LEFT is an initial for RIGHT.
            if (
                    len(left_token) == 1
                    and right_token.startswith(left_token)
            ):
                continue

            # RIGHT is an initial for LEFT.
            if (
                    len(right_token) == 1
                    and left_token.startswith(right_token)
            ):
                continue

            return False

        return True

    # ----------------------------------------------------------
    # Canonicalization Helpers
    # ----------------------------------------------------------

    def _highest_confidence(self, confidences):

        ranking = {
            "High": 3,
            "Medium": 2,
            "Low": 1
        }

        confidences = [
            c
            for c in confidences
            if pd.notna(c)
        ]

        if not confidences:
            return None

        return max(
            confidences,
            key=lambda x: ranking.get(x, 0)
        )

    """
    Score a name according to how informative it is.

    Higher score = preferred canonical name.
    """
    def _name_score(self, name):

        if pd.isna(name):
            return 0

        score = 0

        # Longer names are usually better
        score += len(name)

        # Reward middle initials
        if re.search(r"\b[A-Z]\b", name):
            score += 5

        # Reward suffixes
        if re.search(r"\b(JR|SR|II|III|IV|V)\b", name):
            score += 5

        return score

    ############################################################
    # Finalize Entities
    ############################################################

    # Create the finalized entities table and update the entity occurrences table
    # to link each occurrence to its final entity id.
    def _finalize_entities(self, resolved_entities):
        """
        Assign final entity IDs and create a mapping from each source
        occurrence_id to its resolved entity_id.

        Returns
        -------
        entities : pandas.DataFrame
            Final database-ready entities table.

        occurrence_to_entity : dict
            Maps occurrence_id -> entity_id.
        """

        entities = resolved_entities.copy()

        # Deterministic ordering before assigning IDs
        entities = entities.sort_values(
            by=[
                "canonical_name",
                "canonical_address",
                "entity_type"
            ],
            kind="stable"
        ).reset_index(drop=True)

        # Final entity IDs are assigned only after all merging is complete.
        entities.insert(
            0,
            "entity_id",
            range(1, len(entities) + 1)
        )

        occurrence_to_entity = {}

        for _, row in entities.iterrows():

            entity_id = row["entity_id"]

            for occurrence_id in row["_occurrence_ids"]:

                if occurrence_id in occurrence_to_entity:
                    raise ValueError(
                        f"Occurrence {occurrence_id} was assigned "
                        "to more than one entity."
                    )

                occurrence_to_entity[occurrence_id] = entity_id

        # Internal resolution bookkeeping should not appear in
        # the final database table.
        entities = entities.drop(
            columns="_occurrence_ids"
        )

        entities = entities[
            [
                "entity_id",
                "canonical_name",
                "entity_type",
                "canonical_address",
                "organization_type",
                "organization_classification_confidence",
                "occurrence_count"
            ]
        ]

        return entities, occurrence_to_entity
    ############################################################
    # Stage 4
    # Parcel Entity Roles
    ############################################################

    def _create_parcel_entity_roles(self,
                                    entity_occurrences,
                                    entities):
        raise NotImplementedError

    ############################################################
    # Stage 5
    # Association Evidence
    ############################################################

    def _create_association_evidence(self,
                                     entity_occurrences,
                                     entities):
        raise NotImplementedError

    ############################################################
    # Stage 5
    # Final Entity Associations
    ############################################################

    def _create_entity_associations(self,
                                    association_evidence):
        raise NotImplementedError