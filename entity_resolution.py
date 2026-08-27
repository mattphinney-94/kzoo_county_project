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
            r"^FBO\b.*\bIRA\b$": (
                "Retirement Account",
                "High"
            ),

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

            r"\bREVITALIZATION\b": ("Other Organization", "Medium"),

            r"\bRESTAURANT\b": ("Other Organization", "Medium"),

            r"\bMGT\s+SERV\b": (
                "Other Organization",
                "Medium"
            ),

            # ----------------------------------------------------------
            # Trusts and estates
            # ----------------------------------------------------------

            r"\bTRUST\b": ("Trust", "Medium"),
            r"\bTRST\b": ("Trust", "Medium"),

            r"\bESTATE\b": ("Estate", "Medium"),
            r"\bESTATES\b": ("Estate", "Medium")
        }

        # This is used to classify specific troublesome entities that aren't
        # handled correctly by the entity resolution algorithm.
        self.entity_type_overrides = {
            "CASH N A FLASH": "Organization",
            "MICHIGAN FAST CASH FLIP": "Organization",
            "HOPE THRU NAVIGATION": "Organization",
            "PAYMENT IN LIEU OF TAXES": "Unknown",
            "FIRE HISTORICAL & CULTURAL ARTS": "Organization"
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

        # Create the parcel_entity_roles dataframe
        parcel_entity_roles = (
            self._create_parcel_entity_roles(
                entity_occurrences,
                entities
            )
        )

        # Later stages
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

    # ----------------------------------------------------------
    # Orchestration
    # ----------------------------------------------------------

    def _create_entity_occurrences(self, clean_df):

        # Extract one row per non-empty source-cell occurrence.
        entity_occurrences = self._extract_entity_occurrences(
            clean_df
        )

        # Classify the original source occurrences.
        entity_occurrences = self._classify_entity_type(
            entity_occurrences
        )

        # Replace safely parseable Joint occurrences with their
        # derived individual Person occurrences.
        entity_occurrences = self._expand_joint_occurrences(
            entity_occurrences,
            allowed_confidences=("High", "Medium")
        )

        # Assign organization subtype information to the final
        # occurrence rows.
        entity_occurrences = self._classify_organizations(
            entity_occurrences
        )

        # Add address provenance.
        entity_occurrences = self._assign_address_source(
            entity_occurrences
        )

        # occurrence_id represents the post-decomposition occurrence
        # table, so assign it last.
        entity_occurrences = self._assign_occurrence_ids(
            entity_occurrences
        )

        return entity_occurrences

    # ----------------------------------------------------------
    # Entity Occurrence Extraction and Source Lineage
    # ----------------------------------------------------------

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

            # Preserve the original source value even if entity_name
            # is later transformed or decomposed.
            temp["source_entity_name"] = temp["entity_name"]

            # Preserve the source field as additional provenance.
            temp["source_column"] = column

            tables.append(temp)

        entity_occurrences = pd.concat(
            tables,
            ignore_index=True
        )

        entity_occurrences = entity_occurrences[
            entity_occurrences["entity_name"] != ""
            ].copy()

        # Each row currently represents exactly one non-empty
        # source-cell occurrence. Preserve that identity before any
        # later decomposition creates additional rows.
        entity_occurrences = entity_occurrences.reset_index(
            drop=True
        )

        entity_occurrences["source_occurrence_id"] = (
                entity_occurrences.index + 1
        )

        return entity_occurrences

    # ----------------------------------------------------------
    # Entity Type Classification
    # ----------------------------------------------------------

    def _classify_entity_type(self, entity_occurrences):
        """
        Classify entity occurrences as:

            Person
            Organization
            Joint
            Unknown

        Explicit overrides take precedence over generalized rules.
        """

        entity_occurrences = entity_occurrences.copy()

        # Default
        entity_occurrences["entity_type"] = "Unknown"

        # ----------------------------------------------------------
        # Organization
        # ----------------------------------------------------------

        organization_mask = (
            entity_occurrences["entity_name"]
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
        # Joint / multiple-party records
        # ----------------------------------------------------------

        unknown_mask = (
                entity_occurrences["entity_type"]
                == "Unknown"
        )

        joint_mask = (
                unknown_mask
                &
                entity_occurrences[
                    "entity_name"
                ].apply(
                    self._looks_like_joint_name
                )
        )

        entity_occurrences.loc[
            joint_mask,
            "entity_type"
        ] = "Joint"

        # ----------------------------------------------------------
        # Person
        # ----------------------------------------------------------

        unknown_mask = (
                entity_occurrences["entity_type"]
                == "Unknown"
        )

        person_like = (
            entity_occurrences.loc[
                unknown_mask,
                "entity_name"
            ]
            .apply(self._looks_like_person_name)
        )

        person_indexes = (
            person_like[
                person_like
            ]
            .index
        )

        entity_occurrences.loc[
            person_indexes,
            "entity_type"
        ] = "Person"

        # ----------------------------------------------------------
        # Explicit overrides
        # ----------------------------------------------------------

        overrides = (
            entity_occurrences["entity_name"]
            .map(self.entity_type_overrides)
        )

        valid_entity_types = {
            "Person",
            "Organization",
            "Joint",
            "Unknown"
        }

        invalid_overrides = (
                set(overrides.dropna())
                - valid_entity_types
        )

        if invalid_overrides:
            raise ValueError(
                "Invalid entity type(s) found in "
                f"entity_type_overrides: {invalid_overrides}"
            )

        override_mask = overrides.notna()

        entity_occurrences.loc[
            override_mask,
            "entity_type"
        ] = overrides.loc[
            override_mask
        ]

        return entity_occurrences

    def _normalize_entity_type_candidate(self, name):
        """
        Create a temporary representation of an entity name for
        entity-type classification.

        This method does not change the source entity_name or its role.
        Routing prefixes and other annotations are removed only so that
        the underlying name can be evaluated as Person, Organization,
        Joint, or Unknown.
        """

        name = self._normalize_match_name(name)

        if not name:
            return ""

        # ----------------------------------------------------------
        # Routing prefixes
        # ----------------------------------------------------------

        # C/O JEREMY SHILTS
        # C/O: JEREMY SHILTS
        name = re.sub(
            r"^C\s*/\s*O\s*:?\s*",
            "",
            name
        )

        # ATTN: TROY BUTLER
        name = re.sub(
            r"^ATTN\s*:?\s*",
            "",
            name
        )

        # % CHARLOTTE A JOSLIN
        name = re.sub(
            r"^%\s*",
            "",
            name
        )

        # ----------------------------------------------------------
        # Known status annotations
        # ----------------------------------------------------------

        name = re.sub(
            r"\s*\((?:LC|LE|DCSD)\)\s*$",
            "",
            name
        )

        # DECEASED
        name = re.sub(
            r"\s*\(?\bDECEASED\b\)?\s*$",
            "",
            name
        )

        # Trailing trustee designation
        name = re.sub(
            r",?\s*\b(?:TRUSTEE|TRSTEE)\b\s*$",
            "",
            name
        )

        # Ownership percentage annotation
        name = re.sub(
            r"\s+\d+(?:\.\d+)?\s*%\s*INT\s*$",
            "",
            name
        )

        # Trailing asterisk
        name = re.sub(
            r"\*+$",
            "",
            name
        )

        # ----------------------------------------------------------
        # FKA wrapper
        # ----------------------------------------------------------

        fka_match = re.fullmatch(
            r"\(\s*FKA\s+(.+?)\s*\)",
            name
        )

        if fka_match:
            name = fka_match.group(1)

        return name.strip(" ,")

    def _looks_like_person_name(self, name):
        """
        Determine whether a source value plausibly represents one individual.

        This method is intentionally less strict than _parse_person_name().

        It is used only for entity-type classification. It does NOT determine
        first-name / last-name orientation and should not be used to merge
        entities.
        """

        name = self._normalize_entity_type_candidate(name)

        if not name:
            return False

        # ----------------------------------------------------------
        # Reject obvious multi-party records
        # ----------------------------------------------------------

        if (
                "&" in name
                or "/" in name
                or ";" in name
                or re.search(
            r"\b(?:AND|ET AL|ET UX)\b",
            name
        )
        ):
            return False

        # ----------------------------------------------------------
        # Reject remaining parenthetical structures
        # ----------------------------------------------------------

        if "(" in name or ")" in name:
            return False

        # ----------------------------------------------------------
        # Clean punctuation used in otherwise normal person names
        # ----------------------------------------------------------

        candidate = name.replace(",", " ")

        candidate = re.sub(
            r"\s+",
            " ",
            candidate
        ).strip()

        tokens = candidate.split()

        if not tokens:
            return False

        # ----------------------------------------------------------
        # Remove a terminal generational suffix
        # ----------------------------------------------------------

        suffixes = {
            "JR",
            "JUNIOR",
            "SR",
            "SENIOR",
            "II",
            "III",
            "IV"
        }

        if tokens[-1] in suffixes:
            tokens = tokens[:-1]

        if not tokens:
            return False

        # ----------------------------------------------------------
        # Basic structural requirements
        # ----------------------------------------------------------

        # One token provides too little information.
        #
        # Examples:
        #     RYAN
        #     LATHAM
        #     BENCHMARK
        #
        # These should remain Unknown unless explicitly overridden.
        if len(tokens) < 2:
            return False

        # Very long strings are too structurally ambiguous for this
        # simple classifier.
        if len(tokens) > 6:
            return False

        # ----------------------------------------------------------
        # Token validation
        # ----------------------------------------------------------

        for token in tokens:

            # Allow letters, apostrophes, and hyphens in names.
            if not re.fullmatch(
                    r"[A-Z]+(?:['-][A-Z]+)*",
                    token
            ):
                return False

        # ----------------------------------------------------------
        # Person-like structure
        # ----------------------------------------------------------

        return True

    def _looks_like_joint_name(self, name):
        """
        Determine whether a source value appears to represent
        multiple parties.

        Routing prefixes and administrative annotations are ignored
        for classification purposes only.
        """

        name = self._normalize_entity_type_candidate(name)

        if not name:
            return False

        if "&" in name:
            return True

        if ";" in name:
            return True

        if re.search(
                r"\bAND\b",
                name
        ):
            return True

        if "/" in name:
            return True

        return False

    # ----------------------------------------------------------
    # Joint Occurrence Decomposition
    # ----------------------------------------------------------

    def _parse_joint_name(self, name):
        """
        Attempt to decompose a Joint entity name into individual people.

        Version 1 intentionally supports only relatively high-confidence
        single-ampersand formats.

        Supported families
        ------------------

        1. Explicit surnames for both people:

            LAST1, FIRST1 [MIDDLE] & LAST2, FIRST2 [MIDDLE]

            Example:
                MASTERS, JANET & BROWN, CHRISTIE

            Produces:
                MASTERS, JANET
                BROWN, CHRISTIE


        2. One explicit shared surname:

            LAST, FIRST1 [MIDDLE] & FIRST2 [MIDDLE]

            Example:
                ALEXANDER, MICHAEL & KELLY

            Produces:
                ALEXANDER, MICHAEL
                ALEXANDER, KELLY


        Ambiguous formats are intentionally left unresolved.

        Returns
        -------
        dict or None

        Successful result:

            {
                "parties": [...],
                "rule": "...",
                "confidence": "High" or "Medium"
            }

        None means the name should remain a Joint occurrence.
        """

        candidate = self._normalize_entity_type_candidate(name)

        if not candidate:
            return None

        # ----------------------------------------------------------
        # Version 1 supports exactly one ampersand
        # ----------------------------------------------------------

        if candidate.count("&") != 1:
            return None

        # Other multi-party separators make the structure too
        # complicated for this version of the parser.
        if ";" in candidate:
            return None

        if "/" in candidate:
            return None

        if re.search(
                r"\b(?:AND|ET AL|ET UX)\b",
                candidate
        ):
            return None

        # ----------------------------------------------------------
        # Split into the two apparent parties
        # ----------------------------------------------------------

        left, right = [
            part.strip(" ,")
            for part in candidate.split("&", 1)
        ]

        if not left or not right:
            return None

        # ----------------------------------------------------------
        # Family 1:
        #
        # LAST1, FIRST1 ... & LAST2, FIRST2 ...
        #
        # Both surnames are explicit.
        # ----------------------------------------------------------

        if candidate.count(",") == 2:

            # Require exactly one comma on each side.
            #
            # This prevents something such as:
            #
            # NUTT, JAMES D, II & SHANNON M
            #
            # from being mistaken for the explicit-surname format.
            if (
                    left.count(",") != 1
                    or right.count(",") != 1
            ):
                return None

            party_1 = left
            party_2 = right

            parsed_1 = self._parse_person_name(
                party_1
            )

            parsed_2 = self._parse_person_name(
                party_2
            )

            # Both resulting names must independently look like
            # parseable individual people.
            if (
                    parsed_1 is None
                    or parsed_2 is None
            ):
                return None

            # If either person is represented only by a one-letter
            # first name, keep the result available for inspection
            # but do not treat it as the highest-confidence case.
            if (
                    len(parsed_1["first_name"]) == 1
                    or len(parsed_2["first_name"]) == 1
            ):
                confidence = "Medium"

            else:
                confidence = "High"

            return {
                "parties": [
                    party_1,
                    party_2
                ],
                "rule": "explicit_surnames_comma",
                "confidence": confidence
            }

        # ----------------------------------------------------------
        # Family 2:
        #
        # LAST, FIRST1 ... & FIRST2 ...
        #
        # The surname before the comma appears to be shared.
        # ----------------------------------------------------------

        if candidate.count(",") == 1:

            # The comma must be on the left side.
            if (
                    left.count(",") != 1
                    or right.count(",") != 0
            ):
                return None

            surname, first_party_given = [
                part.strip()
                for part in left.split(",", 1)
            ]

            if (
                    not surname
                    or not first_party_given
            ):
                return None

            party_1 = (
                f"{surname}, "
                f"{first_party_given}"
            )

            parsed_1 = self._parse_person_name(
                party_1
            )

            if parsed_1 is None:
                return None

            # ------------------------------------------------------
            # Determine whether the right side is safe enough to
            # interpret as another given-name sequence sharing the
            # surname.
            # ------------------------------------------------------

            right_tokens = right.split()

            if not right_tokens:
                return None

            suffixes = {
                "JR",
                "JUNIOR",
                "SR",
                "SENIOR",
                "II",
                "III",
                "IV"
            }

            # ------------------------------------------------------
            # High confidence:
            #
            # ALEXANDER, MICHAEL & KELLY
            #
            # A one-token second party is a strong shared-surname
            # structure, provided the token is more than an initial.
            # ------------------------------------------------------

            if len(right_tokens) == 1:

                if len(right_tokens[0]) == 1:
                    return None

                confidence = "High"


            # ------------------------------------------------------
            # High confidence:
            #
            # SMITH, JOHN & ROBERT JR
            #
            # The second token is clearly a suffix rather than a
            # possible surname.
            # ------------------------------------------------------

            elif (
                    len(right_tokens) == 2
                    and right_tokens[1] in suffixes
            ):

                if len(right_tokens[0]) == 1:
                    return None

                confidence = "High"


            # ------------------------------------------------------
            # Medium confidence:
            #
            # DIPZINSKI, JOSHUA D & ELISABETH A
            #
            # This is likely FIRST + MIDDLE INITIAL.
            #
            # However:
            #
            # GREENMAN, PETER & NICHOLS-HICKS S
            #
            # could instead mean surname + first initial.
            #
            # Therefore retain this as a candidate but do not expand
            # it automatically under the default High-only setting.
            # ------------------------------------------------------

            elif (
                    len(right_tokens) == 2
                    and len(right_tokens[1]) == 1
                    and len(right_tokens[0]) > 1
            ):

                confidence = "Medium"


            # ------------------------------------------------------
            # Medium confidence:
            #
            # LAST, FIRST & SECOND M JR
            # ------------------------------------------------------

            elif (
                    len(right_tokens) == 3
                    and len(right_tokens[1]) == 1
                    and right_tokens[2] in suffixes
                    and len(right_tokens[0]) > 1
            ):

                confidence = "Medium"


            # Everything else is too ambiguous for version 1.
            #
            # Example:
            #
            # KUHN, CHRISTOPHER L & LEE TAYLOR
            #
            # TAYLOR could be a middle name or a surname.
            else:
                return None

            party_2 = (
                f"{surname}, {right}"
            )

            parsed_2 = self._parse_person_name(
                party_2
            )

            if parsed_2 is None:
                return None

            return {
                "parties": [
                    party_1,
                    party_2
                ],
                "rule": "shared_surname_comma",
                "confidence": confidence
            }

        # ----------------------------------------------------------
        # Family 3:
        #
        # Zero-comma, single-ampersand records.
        #
        # Several conservative subfamilies are supported.
        # ----------------------------------------------------------

        if candidate.count(",") == 0:

            left_tokens = left.split()
            right_tokens = right.split()

            if not left_tokens or not right_tokens:
                return None

            suffixes = {
                "JR",
                "JUNIOR",
                "SR",
                "SENIOR",
                "II",
                "III",
                "IV"
            }

            # ------------------------------------------------------
            # 3A. Same leading surname explicitly repeated
            #
            # STECK MARLENE & STECK DORA
            #
            # -> STECK, MARLENE
            # -> STECK, DORA
            #
            # No surname inference is necessary.
            # ------------------------------------------------------

            if (
                    len(left_tokens) >= 2
                    and len(right_tokens) >= 2
                    and left_tokens[0] == right_tokens[0]
            ):

                surname = left_tokens[0]

                party_1 = (
                    f"{surname}, "
                    f"{' '.join(left_tokens[1:])}"
                )

                party_2 = (
                    f"{surname}, "
                    f"{' '.join(right_tokens[1:])}"
                )

                if (
                        self._parse_person_name(party_1) is None
                        or self._parse_person_name(party_2) is None
                ):
                    return None

                return {
                    "parties": [
                        party_1,
                        party_2
                    ],
                    "rule": "explicit_shared_surname_no_comma",
                    "confidence": "High"
                }

            # ------------------------------------------------------
            # 3B. Symmetric surname + first-initial structure
            #
            # SAUNDERS R & FARQUHAR D
            #
            # -> SAUNDERS, R
            # -> FARQUHAR, D
            #
            # Both sides independently have exactly:
            #
            #     SURNAME INITIAL
            #
            # so do not infer a shared surname.
            # ------------------------------------------------------

            if (
                    len(left_tokens) == 2
                    and len(right_tokens) == 2
                    and len(left_tokens[1]) == 1
                    and len(right_tokens[1]) == 1
                    and len(left_tokens[0]) > 1
                    and len(right_tokens[0]) > 1
            ):

                party_1 = (
                    f"{left_tokens[0]}, "
                    f"{left_tokens[1]}"
                )

                party_2 = (
                    f"{right_tokens[0]}, "
                    f"{right_tokens[1]}"
                )

                if (
                        self._parse_person_name(party_1) is None
                        or self._parse_person_name(party_2) is None
                ):
                    return None

                return {
                    "parties": [
                        party_1,
                        party_2
                    ],
                    "rule": "explicit_surnames_initials_no_comma",
                    "confidence": "Medium"
                }

            # ------------------------------------------------------
            # 3C. One-token right side:
            # infer shared leading surname.
            #
            # BURROUGHS CHERYL & HOWARD
            #
            # -> BURROUGHS, CHERYL
            # -> BURROUGHS, HOWARD
            # ------------------------------------------------------

            if (
                    len(left_tokens) >= 2
                    and len(right_tokens) == 1
            ):

                surname = left_tokens[0]

                party_1 = (
                    f"{surname}, "
                    f"{' '.join(left_tokens[1:])}"
                )

                party_2 = (
                    f"{surname}, "
                    f"{right_tokens[0]}"
                )

                if (
                        self._parse_person_name(party_1) is None
                        or self._parse_person_name(party_2) is None
                ):
                    return None

                return {
                    "parties": [
                        party_1,
                        party_2
                    ],
                    "rule": "shared_surname_single_right_name",
                    "confidence": "High"
                }

            # ------------------------------------------------------
            # 3D. Right side = FIRST + MIDDLE INITIAL:
            # infer shared leading surname.
            #
            # BRINKS JOSEPH H & DARLENE L
            #
            # -> BRINKS, JOSEPH H
            # -> BRINKS, DARLENE L
            #
            # The symmetric SURNAME INITIAL & SURNAME INITIAL case
            # was already handled above.
            # ------------------------------------------------------

            if (
                    len(left_tokens) >= 2
                    and len(right_tokens) == 2
                    and len(right_tokens[0]) > 1
                    and len(right_tokens[1]) == 1
            ):

                surname = left_tokens[0]

                party_1 = (
                    f"{surname}, "
                    f"{' '.join(left_tokens[1:])}"
                )

                party_2 = (
                    f"{surname}, "
                    f"{' '.join(right_tokens)}"
                )

                if (
                        self._parse_person_name(party_1) is None
                        or self._parse_person_name(party_2) is None
                ):
                    return None

                return {
                    "parties": [
                        party_1,
                        party_2
                    ],
                    "rule": "shared_surname_initial_no_comma",
                    "confidence": "Medium"
                }

            # ------------------------------------------------------
            # 3E. Shared trailing surname.
            #
            # FRED & LILLIAN COCHRAN
            #
            # -> COCHRAN, FRED
            # -> COCHRAN, LILLIAN
            #
            # This is intentionally limited to cases where the left
            # side contains exactly one token.
            #
            # Do not apply this rule to routing-prefixed source
            # values such as:
            #
            #     C/O SCOFIELD & VAN DENBELDT
            # ------------------------------------------------------

            raw_name = self._normalize_match_name(name)

            has_routing_prefix = bool(
                re.match(
                    r"^(?:C\s*/\s*O|ATTN\s*:|%)",
                    raw_name
                )
            )

            if (
                    len(left_tokens) == 1
                    and len(right_tokens) >= 2
                    and not has_routing_prefix
            ):

                surname = right_tokens[-1]

                person_2_given_tokens = (
                    right_tokens[:-1]
                )

                if not person_2_given_tokens:
                    return None

                party_1 = (
                    f"{surname}, "
                    f"{left_tokens[0]}"
                )

                party_2 = (
                    f"{surname}, "
                    f"{' '.join(person_2_given_tokens)}"
                )

                if (
                        self._parse_person_name(party_1) is None
                        or self._parse_person_name(party_2) is None
                ):
                    return None

                return {
                    "parties": [
                        party_1,
                        party_2
                    ],
                    "rule": "shared_trailing_surname_no_comma",
                    "confidence": "Medium"
                }

            # ------------------------------------------------------
            # Other zero-comma structures remain unresolved.
            # ------------------------------------------------------

            return None

        return None

    def _expand_joint_occurrences(
            self,
            entity_occurrences,
            allowed_confidences=("High",)
    ):
        """
        Replace safely parseable Joint occurrences with individual
        Person occurrences.

        Source-level provenance is preserved.

        Parameters
        ----------
        entity_occurrences : pd.DataFrame
            Entity-occurrence table after entity-type classification
            but before occurrence_id is assigned.

        allowed_confidences : iterable of str
            Parse-confidence levels that are allowed to expand.

            Default:
                ("High",)

            Medium-confidence parses remain as Joint rows so they can
            be audited before being enabled.

        Returns
        -------
        pd.DataFrame
            Expanded entity-occurrence table.

        Notes
        -----
        source_occurrence_id identifies the original source-cell
        occurrence and may therefore appear more than once after
        successful decomposition.

        occurrence_id should be assigned only AFTER this method runs.
        """

        entity_occurrences = (
            entity_occurrences.copy()
        )

        allowed_confidences = set(
            allowed_confidences
        )

        valid_confidences = {
            "High",
            "Medium",
            "Low"
        }

        invalid_confidences = (
                allowed_confidences
                - valid_confidences
        )

        if invalid_confidences:
            raise ValueError(
                "Invalid joint parse confidence level(s): "
                f"{invalid_confidences}"
            )

        # ----------------------------------------------------------
        # Validate expected lineage columns
        # ----------------------------------------------------------

        required_columns = {
            "source_occurrence_id",
            "source_entity_name",
            "source_column",
            "entity_name",
            "entity_type",
            "parcel_number",
            "role",
            "associated_address"
        }

        missing_columns = (
                required_columns
                - set(entity_occurrences.columns)
        )

        if missing_columns:
            raise ValueError(
                "entity_occurrences is missing required "
                "column(s) for Joint decomposition: "
                f"{sorted(missing_columns)}"
            )

        # occurrence_id must represent the post-decomposition
        # occurrence table, so it should not exist yet.
        if "occurrence_id" in entity_occurrences.columns:
            raise ValueError(
                "occurrence_id was assigned before Joint "
                "decomposition. Move occurrence_id assignment "
                "until after _expand_joint_occurrences()."
            )

        # Before expansion, every source occurrence should still
        # correspond to exactly one row.
        if entity_occurrences[
            "source_occurrence_id"
        ].duplicated().any():
            raise ValueError(
                "Duplicate source_occurrence_id values exist before "
                "Joint decomposition. _expand_joint_occurrences() "
                "expects one row per source occurrence as input."
            )

        # ----------------------------------------------------------
        # Prepare audit columns
        # ----------------------------------------------------------

        entity_occurrences[
            "joint_parse_rule"
        ] = ""

        entity_occurrences[
            "joint_parse_confidence"
        ] = ""

        entity_occurrences[
            "joint_expanded"
        ] = False

        entity_occurrences[
            "joint_party_index"
        ] = pd.NA

        entity_occurrences[
            "joint_party_count"
        ] = pd.NA

        # ----------------------------------------------------------
        # Expand safely parseable Joint rows
        # ----------------------------------------------------------

        expanded_rows = []

        for _, row in entity_occurrences.iterrows():

            # Non-Joint rows pass through untouched.
            if row["entity_type"] != "Joint":
                expanded_rows.append(
                    row.to_dict()
                )

                continue

            parse_result = self._parse_joint_name(
                row["entity_name"]
            )

            # ------------------------------------------------------
            # Parser could not safely interpret the Joint name.
            # Keep the original Joint occurrence.
            # ------------------------------------------------------

            if parse_result is None:
                expanded_rows.append(
                    row.to_dict()
                )

                continue

            rule = parse_result["rule"]

            confidence = (
                parse_result["confidence"]
            )

            parties = parse_result["parties"]

            # ------------------------------------------------------
            # Preserve parse metadata even when the confidence is
            # not currently allowed to expand.
            #
            # This makes Medium candidates easy to audit.
            # ------------------------------------------------------

            if confidence not in allowed_confidences:
                unresolved_row = row.copy()

                unresolved_row[
                    "joint_parse_rule"
                ] = rule

                unresolved_row[
                    "joint_parse_confidence"
                ] = confidence

                unresolved_row[
                    "joint_party_count"
                ] = len(parties)

                expanded_rows.append(
                    unresolved_row.to_dict()
                )

                continue

            # ------------------------------------------------------
            # Replace the Joint occurrence with one Person row per
            # successfully parsed party.
            # ------------------------------------------------------

            party_count = len(parties)

            for party_index, party_name in enumerate(
                    parties,
                    start=1
            ):
                new_row = row.copy()

                # entity_name now represents the derived individual.
                #
                # source_entity_name remains untouched and therefore
                # retains the exact original Joint source value.
                new_row[
                    "entity_name"
                ] = party_name

                new_row[
                    "entity_type"
                ] = "Person"

                new_row[
                    "joint_parse_rule"
                ] = rule

                new_row[
                    "joint_parse_confidence"
                ] = confidence

                new_row[
                    "joint_expanded"
                ] = True

                new_row[
                    "joint_party_index"
                ] = party_index

                new_row[
                    "joint_party_count"
                ] = party_count

                expanded_rows.append(
                    new_row.to_dict()
                )

        # ----------------------------------------------------------
        # Rebuild dataframe
        # ----------------------------------------------------------

        expanded_entity_occurrences = pd.DataFrame(
            expanded_rows
        )

        expanded_entity_occurrences = (
            expanded_entity_occurrences
            .reset_index(drop=True)
        )

        return expanded_entity_occurrences

    # ----------------------------------------------------------
    # Organization Subtype Classification
    # ----------------------------------------------------------

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

    def _classify_organization(self, name):

        if name == "":
            return (None, None)

        for pattern, (org_type, confidence) in self.organization_patterns.items():

            if re.search(pattern, name):
                return (org_type, confidence)

        return ("Other Organization", "Low")

    # ----------------------------------------------------------
    # Occurrence Metadata and Finalization
    # ----------------------------------------------------------

    def _assign_address_source(self, entity_occurrences):

        entity_occurrences["address_source"] = (
            entity_occurrences["role"]
            .map(self.address_source_mapping)
        )

        return entity_occurrences

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

            entities = self._merge_missing_street_suffix_variants(
                entities
            )

            entities = self._merge_zip4_variants(
                entities
            )

            entities = self._merge_equivalent_person_name_formats(
                entities
            )

            entities = self._merge_middle_initial_variants(
                entities
            )

            # Organization name normalization
            entities = self._merge_organization_name_variants(
                entities
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

    def _merge_missing_street_suffix_variants(self, entities):
        """
        Merge otherwise identical entities when their addresses differ
        only because one address omits a street suffix.

        Requirements:
            - Entity type must match.
            - Canonical name must match exactly.
            - Street base must match exactly.
            - Locality must match exactly.
            - Unit information must match exactly.
            - At least one address must omit the street suffix.
            - Exactly one distinct nonblank street suffix may exist.

        Example that can merge:

            WIDGER JAMES LEROY
            214 MARSHALL, ALLEGAN, MI 49010

            WIDGER JAMES LEROY
            214 MARSHALL ST, ALLEGAN, MI 49010

        Example that will NOT merge:

            214 MARSHALL ST, ALLEGAN, MI 49010
            214 MARSHALL AVE, ALLEGAN, MI 49010

        because there are conflicting known suffixes.
        """

        entities = entities.copy().reset_index(
            drop=True
        )

        parsed_rows = []

        # ----------------------------------------------------------
        # Parse candidate addresses
        # ----------------------------------------------------------

        for index, row in entities.iterrows():

            parsed = self._parse_address_for_suffix_matching(
                row["canonical_address"]
            )

            if parsed is None:
                continue

            parsed_rows.append({
                "row_index": index,
                "entity_type": row["entity_type"],
                "canonical_name": row["canonical_name"],
                "canonical_address": row["canonical_address"],
                "street_base": parsed["street_base"],
                "street_suffix": parsed["street_suffix"],
                "unit": parsed["unit"],
                "locality": parsed["locality"]
            })

        if not parsed_rows:
            return entities

        candidates = pd.DataFrame(
            parsed_rows
        )

        # ----------------------------------------------------------
        # Find unambiguous missing-suffix groups
        # ----------------------------------------------------------

        grouping_columns = [
            "entity_type",
            "canonical_name",
            "street_base",
            "unit",
            "locality"
        ]

        for _, group in candidates.groupby(
                grouping_columns,
                dropna=False,
                sort=False
        ):

            if len(group) < 2:
                continue

            suffixes = set(
                group["street_suffix"]
            )

            nonblank_suffixes = {
                suffix
                for suffix in suffixes
                if suffix
            }

            # There must be at least one suffix-free representation.
            if "" not in suffixes:
                continue

            # Exactly one known suffix must exist.
            #
            # Safe:
            #     MARSHALL
            #     MARSHALL ST
            #
            # Unsafe:
            #     MARSHALL
            #     MARSHALL ST
            #     MARSHALL AVE
            if len(nonblank_suffixes) != 1:
                continue

            known_suffix = next(
                iter(nonblank_suffixes)
            )

            # ------------------------------------------------------
            # Use an address that actually appeared in the data.
            # Do not synthesize a new canonical address.
            # ------------------------------------------------------

            suffixed_rows = group[
                group["street_suffix"]
                == known_suffix
                ]

            suffixed_addresses = (
                suffixed_rows[
                    "canonical_address"
                ]
                .drop_duplicates()
                .tolist()
            )

            # More than one supposedly equivalent complete address
            # means there is some additional variation that this rule
            # should not resolve.
            if len(suffixed_addresses) != 1:
                continue

            preferred_address = (
                suffixed_addresses[0]
            )

            # Assign the known complete address only to rows whose
            # street suffix is missing.
            blank_suffix_rows = group[
                group["street_suffix"] == ""
                ]

            for row_index in blank_suffix_rows[
                "row_index"
            ]:
                entities.at[
                    row_index,
                    "canonical_address"
                ] = preferred_address

        # ----------------------------------------------------------
        # Rows whose missing suffix was resolved can now collapse
        # using the ordinary exact-key merge infrastructure.
        # ----------------------------------------------------------

        entities = self._merge_on_key(
            entities,
            [
                "entity_type",
                "canonical_name",
                "canonical_address"
            ]
        )

        return entities

    def _merge_zip4_variants(self, entities):
        """
        Merge exactly same-named entities whose canonical addresses differ
        only because one contains ZIP+4 information and another contains
        only the corresponding five-digit ZIP.

        Requirements:
            - Entity type must match.
            - Canonical name must match exactly.
            - All address content before the ZIP must match exactly.
            - Five-digit ZIP must match.
            - At least one address must omit ZIP+4.
            - Exactly one distinct nonblank ZIP+4 may exist.

        The ZIP+4 address is preferred because it contains more information,
        but only an address that actually occurred in the data is used.

        Examples that can merge:

            10440 N 24TH ST, PLAINWELL, MI 49080
            10440 N 24TH ST, PLAINWELL, MI 49080-8903

            PO BOX 365, GALESBURG, MI 49053
            PO BOX 365, GALESBURG, MI 49053-0365
        """

        entities = entities.copy().reset_index(
            drop=True
        )

        candidate_rows = []

        # ----------------------------------------------------------
        # Build ZIP-insensitive address representations
        # ----------------------------------------------------------

        for index, row in entities.iterrows():

            address = row["canonical_address"]

            parsed = self._parse_zip4_for_matching(
                address
            )

            if parsed is None:
                continue

            candidate_rows.append({
                "row_index":
                    index,

                "entity_type":
                    row["entity_type"],

                "canonical_name":
                    row["canonical_name"],

                "canonical_address":
                    address,

                "address_match_key":
                    parsed["address_match_key"],

                "zip4":
                    parsed["zip4"]
            })

        if not candidate_rows:
            return entities

        candidates = pd.DataFrame(
            candidate_rows
        )

        # ----------------------------------------------------------
        # Find unambiguous ZIP+4 variant groups
        # ----------------------------------------------------------

        group_columns = [
            "entity_type",
            "canonical_name",
            "address_match_key"
        ]

        for _, group in candidates.groupby(
                group_columns,
                dropna=False,
                sort=False
        ):

            if len(group) < 2:
                continue

            zip4_values = set(
                group["zip4"]
            )

            nonblank_zip4_values = {
                zip4
                for zip4 in zip4_values
                if zip4
            }

            # This rule requires both:
            #
            #     ZIP5-only
            #     ZIP5+4
            #
            if "" not in zip4_values:
                continue

            # Do not resolve conflicting ZIP+4 values.
            #
            # Example:
            #
            #     49048
            #     49048-1111
            #     49048-2222
            #
            if len(nonblank_zip4_values) != 1:
                continue

            known_zip4 = next(
                iter(nonblank_zip4_values)
            )

            # Find the actual source address containing the unique ZIP+4.
            zip4_rows = group[
                group["zip4"] == known_zip4
                ]

            preferred_addresses = (
                zip4_rows[
                    "canonical_address"
                ]
                .drop_duplicates()
                .tolist()
            )

            # Some additional unexplained address variation exists.
            # Leave it unresolved.
            if len(preferred_addresses) != 1:
                continue

            preferred_address = (
                preferred_addresses[0]
            )

            # Give every member of this proven-equivalent group the
            # more informative address representation.
            for row_index in group[
                "row_index"
            ]:
                entities.at[
                    row_index,
                    "canonical_address"
                ] = preferred_address

        # Rows standardized above can now collapse using persistent,
        # ordinary entity columns.
        return self._merge_on_key(
            entities,
            [
                "entity_type",
                "canonical_name",
                "canonical_address"
            ]
        )

    def _merge_equivalent_person_name_formats(self, entities):
        """
        Merge Person entities whose names are formatted differently but
        parse to exactly the same person-name components.

        ZIP5 and ZIP+4 versions of an otherwise identical address are
        considered equivalent when there is no conflicting ZIP+4 value.

        Missing versus explicit name information is NOT treated as
        equivalent.

        Examples that can merge:

            DERRING III, ALBERT
            DERRING, ALBERT III

        Examples that will NOT merge:

            DERRING, ALBERT
            DERRING, ALBERT III

            LINDSEY, WILLIAM B
            LINDSEY, WILLIAM B JR
        """

        entities = entities.copy().reset_index(
            drop=True
        )

        candidate_rows = []

        for index, row in entities.iterrows():

            if row["entity_type"] != "Person":
                continue

            address = row["canonical_address"]

            if (
                    pd.isna(address)
                    or str(address).strip() == ""
            ):
                continue

            parsed_name = self._parse_person_name(
                row["canonical_name"]
            )

            if parsed_name is None:
                continue

            parsed_address = (
                self._parse_zip4_for_matching(
                    address
                )
            )

            if parsed_address is None:
                continue

            candidate_rows.append({
                "row_index":
                    index,

                "canonical_address":
                    address,

                "address_match_key":
                    parsed_address[
                        "address_match_key"
                    ],

                "zip4":
                    parsed_address["zip4"],

                "last_name":
                    parsed_name["last_name"],

                "first_name":
                    parsed_name["first_name"],

                "middle_tokens":
                    parsed_name["middle_tokens"],

                "suffix":
                    parsed_name["suffix"]
            })

        if not candidate_rows:
            return entities

        candidates = pd.DataFrame(
            candidate_rows
        )

        groups_to_merge = []

        group_columns = [
            "address_match_key",
            "last_name",
            "first_name",
            "middle_tokens",
            "suffix"
        ]

        for _, group in candidates.groupby(
                group_columns,
                dropna=False,
                sort=False
        ):

            if len(group) < 2:
                continue

            indexes = (
                group["row_index"]
                .tolist()
            )

            canonical_names = {
                entities.at[
                    index,
                    "canonical_name"
                ]
                for index in indexes
            }

            canonical_addresses = {
                entities.at[
                    index,
                    "canonical_address"
                ]
                for index in indexes
            }

            # Nothing actually differs.
            if (
                    len(canonical_names) < 2
                    and len(canonical_addresses) < 2
            ):
                continue

            # ------------------------------------------------------
            # Reject conflicting ZIP+4 information
            # ------------------------------------------------------

            nonblank_zip4_values = {
                zip4
                for zip4 in group["zip4"]
                if zip4
            }

            if len(nonblank_zip4_values) > 1:
                continue

            # ------------------------------------------------------
            # Prefer the actual ZIP+4 representation when available
            # ------------------------------------------------------

            if len(nonblank_zip4_values) == 1:

                known_zip4 = next(
                    iter(nonblank_zip4_values)
                )

                preferred_addresses = (
                    group.loc[
                        group["zip4"]
                        == known_zip4,
                        "canonical_address"
                    ]
                    .drop_duplicates()
                    .tolist()
                )

                if len(preferred_addresses) != 1:
                    continue

                preferred_address = (
                    preferred_addresses[0]
                )

                for row_index in indexes:
                    entities.at[
                        row_index,
                        "canonical_address"
                    ] = preferred_address

            groups_to_merge.append(
                indexes
            )

        return self._collapse_index_groups(
            entities,
            groups_to_merge
        )

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

    # ----------------------------------------------------------
    # Resolution Infrastructure
    # ----------------------------------------------------------

    def _merge_organization_name_variants(self, entities):
        """
        Merge Organization entities at the same canonical address when
        lightweight punctuation normalization and known organization-name
        abbreviation expansion produce the same matching representation.

        Current abbreviation expansions:

            CORP -> CORPORATION
            INC  -> INCORPORATED
            CO   -> COMPANY

        This rule applies only to Organization entities.
        """

        entities = entities.copy().reset_index(
            drop=True
        )

        organization_mask = (
                entities["entity_type"]
                == "Organization"
        )

        organizations = (
            entities.loc[
                organization_mask
            ]
            .copy()
        )

        other_entities = (
            entities.loc[
                ~organization_mask
            ]
            .copy()
        )

        if organizations.empty:
            return entities

        organizations["match_name"] = (
            organizations["canonical_name"]
            .apply(
                self._expand_common_abbreviations
            )
        )

        organizations = self._merge_on_key(
            organizations,
            [
                "entity_type",
                "match_name",
                "canonical_address"
            ]
        )

        organizations = organizations.drop(
            columns="match_name",
            errors="ignore"
        )

        result = pd.concat(
            [
                organizations,
                other_entities
            ],
            ignore_index=True
        )

        # Preserve the original entity-table schema.
        result = result[
            entities.columns
        ]

        return result.reset_index(
            drop=True
        )

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

        A row may belong to at most one merge group during a single
        resolution-rule pass. Overlapping groups indicate an error
        in the rule that constructed groups_to_merge.
        """

        entities = entities.copy().reset_index(
            drop=True
        )

        replacements = {}

        # Indexes that should be omitted from the output because they
        # were merged into another row.
        consumed_indexes = set()

        # Every index assigned to a merge group, including anchors.
        # This is used only to detect overlapping merge groups.
        claimed_indexes = set()

        for indexes in groups_to_merge:

            # Remove duplicate indexes within the same proposed group
            # while preserving order.
            indexes = list(
                dict.fromkeys(indexes)
            )

            if len(indexes) < 2:
                continue

            index_set = set(indexes)

            # ----------------------------------------------------------
            # Validate indexes
            # ----------------------------------------------------------

            invalid_indexes = (
                    index_set
                    - set(entities.index)
            )

            if invalid_indexes:
                raise ValueError(
                    "Merge group contains invalid entity row "
                    f"index(es): {sorted(invalid_indexes)}"
                )

            # ----------------------------------------------------------
            # Prevent overlapping independent merge groups
            # ----------------------------------------------------------

            overlap = (
                    index_set
                    & claimed_indexes
            )

            if overlap:
                raise ValueError(
                    "An entity was assigned to more than one "
                    "merge group during the same resolution rule. "
                    f"Overlapping row index(es): "
                    f"{sorted(overlap)}"
                )

            # Claim every row in the group, including the anchor.
            claimed_indexes.update(
                index_set
            )

            # ----------------------------------------------------------
            # Merge the approved group
            # ----------------------------------------------------------

            group = entities.loc[
                indexes
            ]

            merged_row = self._merge_group(
                group
            )

            # Keep the merged entity in the position of the first
            # member of the group.
            anchor_index = indexes[0]

            replacements[
                anchor_index
            ] = merged_row

            # Every other member disappears from the output.
            consumed_indexes.update(
                indexes[1:]
            )

        # --------------------------------------------------------------
        # Rebuild the entity table
        # --------------------------------------------------------------

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

        result = pd.DataFrame(
            output_rows
        )

        # Preserve the original schema and column order.
        for column in entities.columns:

            if column not in result.columns:
                result[column] = None

        result = result[
            entities.columns
        ]

        return result.reset_index(
            drop=True
        )

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

    def _normalize_zip4_for_matching(self, address):
        """
        Create an address representation for matching in which ZIP+4
        is reduced to its five-digit ZIP.

        This does not modify the canonical address stored in the
        final entities table.

        Examples
        --------
        3041 N 26TH ST, KALAMAZOO, MI 49048-4827
            -> 3041 N 26TH ST, KALAMAZOO, MI 49048

        3041 N 26TH ST, KALAMAZOO, MI 49048
            -> unchanged

        PO BOX 365, GALESBURG, MI 49053-0365
            -> PO BOX 365, GALESBURG, MI 49053
        """

        if pd.isna(address):
            return ""

        address = str(address).strip()

        if not address:
            return ""

        return re.sub(
            r"(\b\d{5})-\d{4}\b",
            r"\1",
            address
        )

    def _parse_zip4_for_matching(self, address):
        """
        Parse a normalized mailing address for ZIP+4 matching.

        Returns
        -------
        dict or None

        {
            "address_match_key": address with ZIP+4 reduced to ZIP5,
            "zip5": five-digit ZIP,
            "zip4": four-digit extension or ""
        }

        The canonical address itself is not modified here.
        """

        if pd.isna(address):
            return None

        address = str(address).strip()

        if not address:
            return None

        match = re.search(
            r"^(.*\D)(\d{5})(?:-(\d{4}))?$",
            address
        )

        if match is None:
            return None

        address_prefix = match.group(1)
        zip5 = match.group(2)
        zip4 = match.group(3) or ""

        return {
            "address_match_key":
                f"{address_prefix}{zip5}".strip(),

            "zip5":
                zip5,

            "zip4":
                zip4
        }

    def _parse_address_for_suffix_matching(self, address):
        """
        Parse a normalized mailing address into components used only
        for missing-street-suffix entity resolution.

        Returns None for addresses that cannot be interpreted safely.

        The original canonical_address is never modified here.
        """

        STREET_SUFFIXES = {
            "ST",
            "AVE",
            "RD",
            "DR",
            "BLVD",
            "LN",
            "CT",
            "CIR",
            "PL",
            "PKWY",
            "TER",
            "HWY",
            "WAY",
            "TRL"
        }

        UNIT_MARKERS = {
            "APT",
            "STE",
            "UNIT",
            "BLDG",
            "FL",
            "RM"
        }

        if pd.isna(address):
            return None

        address = str(address).strip()

        if not address:
            return None

        parts = [
            part.strip()
            for part in address.split(",")
        ]

        # Require at least:
        #
        #     street, locality
        #
        # Example:
        #     214 MARSHALL ST, ALLEGAN, MI 49010
        if len(parts) < 2:
            return None

        street_line = parts[0]

        # PO Boxes do not participate in street-suffix matching.
        if street_line.startswith("PO BOX"):
            return None

        locality = ", ".join(parts[1:])

        tokens = street_line.split()

        if len(tokens) < 2:
            return None

        # Require the first street token to contain a number.
        #
        # This prevents the rule from attempting to interpret
        # non-street address-like strings.
        if not any(
                character.isdigit()
                for character in tokens[0]
        ):
            return None

        # ----------------------------------------------------------
        # Separate unit information
        # ----------------------------------------------------------

        unit_index = None

        for i, token in enumerate(tokens):

            if (
                    token in UNIT_MARKERS
                    or token.startswith("#")
            ):
                unit_index = i
                break

        if unit_index is not None:

            street_tokens = tokens[:unit_index]
            unit_tokens = tokens[unit_index:]

        else:

            street_tokens = tokens
            unit_tokens = []

        if len(street_tokens) < 2:
            return None

        # ----------------------------------------------------------
        # Detect the street suffix
        # ----------------------------------------------------------

        if street_tokens[-1] in STREET_SUFFIXES:

            street_suffix = street_tokens[-1]
            street_base_tokens = street_tokens[:-1]

        else:

            street_suffix = ""
            street_base_tokens = street_tokens

        if not street_base_tokens:
            return None

        return {
            "street_base": " ".join(
                street_base_tokens
            ),
            "street_suffix": street_suffix,
            "unit": " ".join(
                unit_tokens
            ),
            "locality": locality
        }

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
        if re.search(r"\b(JR|SR|II|III|IV)\b", name):
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

    def _create_parcel_entity_roles(
            self,
            entity_occurrences,
            entities
    ):
        """
        Create the parcel-to-entity role junction table.

        Grain
        -----
        One row represents one unique relationship between:

            parcel_number
            entity_id
            role

        Multiple source occurrences that resolve to the same entity
        on the same parcel in the same role are collapsed into one
        relationship.

        Detailed source provenance remains in entity_occurrences.
        """

        # ----------------------------------------------------------
        # Validate required columns
        # ----------------------------------------------------------

        required_occurrence_columns = {
            "parcel_number",
            "entity_id",
            "role"
        }

        missing_occurrence_columns = (
                required_occurrence_columns
                - set(entity_occurrences.columns)
        )

        if missing_occurrence_columns:
            raise ValueError(
                "entity_occurrences is missing required "
                "column(s) for parcel entity roles: "
                f"{sorted(missing_occurrence_columns)}"
            )

        if "entity_id" not in entities.columns:
            raise ValueError(
                "entities must contain entity_id before "
                "parcel entity roles are created."
            )

        # ----------------------------------------------------------
        # Validate entity IDs
        # ----------------------------------------------------------

        if entity_occurrences[
            "entity_id"
        ].isna().any():
            raise ValueError(
                "Cannot create parcel entity roles because "
                "some entity occurrences do not have an entity_id."
            )

        if entities[
            "entity_id"
        ].duplicated().any():
            raise ValueError(
                "entities contains duplicate entity_id values."
            )

        valid_entity_ids = set(
            entities["entity_id"]
        )

        occurrence_entity_ids = set(
            entity_occurrences["entity_id"]
        )

        invalid_entity_ids = (
                occurrence_entity_ids
                - valid_entity_ids
        )

        if invalid_entity_ids:
            raise ValueError(
                "entity_occurrences contains entity_id values "
                "that do not exist in entities: "
                f"{sorted(invalid_entity_ids)[:10]}"
            )

        # ----------------------------------------------------------
        # Validate roles
        # ----------------------------------------------------------

        valid_roles = {
            info["role"]
            for info in self.role_mapping.values()
        }

        occurrence_roles = set(
            entity_occurrences["role"]
            .dropna()
        )

        invalid_roles = (
                occurrence_roles
                - valid_roles
        )

        if invalid_roles:
            raise ValueError(
                "Unexpected parcel entity role(s): "
                f"{sorted(invalid_roles)}"
            )

        if entity_occurrences[
            "role"
        ].isna().any():
            raise ValueError(
                "Cannot create parcel entity roles because "
                "some entity occurrences have a missing role."
            )

        # ----------------------------------------------------------
        # Create unique parcel/entity/role relationships
        # ----------------------------------------------------------

        parcel_entity_roles = (
            entity_occurrences[
                [
                    "parcel_number",
                    "entity_id",
                    "role"
                ]
            ]
            .drop_duplicates()
            .sort_values(
                by=[
                    "parcel_number",
                    "entity_id",
                    "role"
                ],
                kind="stable"
            )
            .reset_index(drop=True)
        )

        return parcel_entity_roles
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