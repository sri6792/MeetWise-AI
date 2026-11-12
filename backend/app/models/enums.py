from enum import Enum


class MeetingStatus(str, Enum):
    CREATED = "created"
    RESEARCHING = "researching"
    READY = "ready"
    FAILED = "failed"


class EvidenceLabel(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_SUPPORTED = "partially_supported"
    NEEDS_VERIFICATION = "needs_verification"
    POTENTIALLY_OUTDATED = "potentially_outdated"


class Freshness(str, Enum):
    RECENT = "recent"
    POTENTIALLY_OUTDATED = "potentially_outdated"
    UNKNOWN = "unknown"  # used when the source gives no publication date


class SourceCategory(str, Enum):
    NEWS = "news"
    COMPANY = "company"
    PERSON = "person"
    OTHER = "other"
