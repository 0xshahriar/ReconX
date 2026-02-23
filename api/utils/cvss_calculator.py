"""
ReconX CVSS Calculator
Calculates CVSS 3.1 scores
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

class AttackVector(Enum):
    NETWORK = "N"
    ADJACENT = "A"
    LOCAL = "L"
    PHYSICAL = "P"

class AttackComplexity(Enum):
    LOW = "L"
    HIGH = "H"

class PrivilegesRequired(Enum):
    NONE = "N"
    LOW = "L"
    HIGH = "H"

class UserInteraction(Enum):
    NONE = "N"
    REQUIRED = "R"

class Scope(Enum):
    UNCHANGED = "U"
    CHANGED = "C"

class Impact(Enum):
    HIGH = "H"
    LOW = "L"
    NONE = "N"

@dataclass
class CVSSVector:
    attack_vector: AttackVector = AttackVector.NETWORK
    attack_complexity: AttackComplexity = AttackComplexity.LOW
    privileges_required: PrivilegesRequired = PrivilegesRequired.NONE
    user_interaction: UserInteraction = UserInteraction.NONE
    scope: Scope = Scope.UNCHANGED
    confidentiality: Impact = Impact.HIGH
    integrity: Impact = Impact.HIGH
    availability: Impact = Impact.HIGH

class CVSSCalculator:
    """CVSS 3.1 Base Score Calculator"""
    
    # Metric weights
    AV_WEIGHTS = {AttackVector.NETWORK: 0.85, AttackVector.ADJACENT: 0.62,
                  AttackVector.LOCAL: 0.55, AttackVector.PHYSICAL: 0.2}
    AC_WEIGHTS = {AttackComplexity.LOW: 0.77, AttackComplexity.HIGH: 0.44}
    PR_WEIGHTS = {
        Scope.UNCHANGED: {PrivilegesRequired.NONE: 0.85, PrivilegesRequired.LOW: 0.62, 
                         PrivilegesRequired.HIGH: 0.27},
        Scope.CHANGED: {PrivilegesRequired.NONE: 0.85, PrivilegesRequired.LOW: 0.68,
                       PrivilegesRequired.HIGH: 0.5}
    }
    UI_WEIGHTS = {UserInteraction.NONE: 0.85, UserInteraction.REQUIRED: 0.62}
    IMPACT_WEIGHTS = {Impact.HIGH: 0.56, Impact.LOW: 0.22, Impact.NONE: 0}
    
    def calculate_base_score(self, vector: CVSSVector) -> float:
        """Calculate CVSS 3.1 base score"""
        # Impact Sub-Score (ISS)
        iss = 1 - ((1 - self.IMPACT_WEIGHTS[vector.confidentiality]) * 
                   (1 - self.IMPACT_WEIGHTS[vector.integrity]) * 
                   (1 - self.IMPACT_WEIGHTS[vector.availability]))
        
        # Impact
        if vector.scope == Scope.UNCHANGED:
            impact = 6.42 * iss
        else:
            impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
        
        # Exploitability
        exploitability = (8.22 * self.AV_WEIGHTS[vector.attack_vector] * 
                         self.AC_WEIGHTS[vector.attack_complexity] * 
                         self.PR_WEIGHTS[vector.scope][vector.privileges_required] * 
                         self.UI_WEIGHTS[vector.user_interaction])
        
        # Base Score
        if impact <= 0:
            base_score = 0
        elif vector.scope == Scope.UNCHANGED:
            base_score = min((impact + exploitability), 10)
        else:
            base_score = min(1.08 * (impact + exploitability), 10)
        
        return round(base_score, 1)
    
    def get_severity(self, score: float) -> str:
        """Get severity rating from score"""
        if score == 0:
            return "none"
        elif score < 4:
            return "low"
        elif score < 7:
            return "medium"
        elif score < 9:
            return "high"
        else:
            return "critical"
    
    def vector_to_string(self, vector: CVSSVector) -> str:
        """Convert vector to CVSS string format"""
        return (f"CVSS:3.1/AV:{vector.attack_vector.value}/"
                f"AC:{vector.attack_complexity.value}/"
                f"PR:{vector.privileges_required.value}/"
                f"UI:{vector.user_interaction.value}/"
                f"S:{vector.scope.value}/"
                f"C:{vector.confidentiality.value}/"
                f"I:{vector.integrity.value}/"
                f"A:{vector.availability.value}")
    
    def string_to_vector(self, vector_string: str) -> CVSSVector:
        """Parse CVSS string to vector"""
        # Simplified parser - full implementation would be more robust
        vector = CVSSVector()
        parts = vector_string.split('/')
        
        for part in parts:
            if ':' not in part:
                continue
            metric, value = part.split(':')
            
            if metric == 'AV':
                vector.attack_vector = AttackVector(value)
            elif metric == 'AC':
                vector.attack_complexity = AttackComplexity(value)
            elif metric == 'PR':
                vector.privileges_required = PrivilegesRequired(value)
            elif metric == 'UI':
                vector.user_interaction = UserInteraction(value)
            elif metric == 'S':
                vector.scope = Scope(value)
            elif metric == 'C':
                vector.confidentiality = Impact(value)
            elif metric == 'I':
                vector.integrity = Impact(value)
            elif metric == 'A':
                vector.availability = Impact(value)
        
        return vector
