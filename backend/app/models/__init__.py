# Import tất cả models để SQLAlchemy Base.metadata nhận diện
# — cần thiết để Alembic autogenerate migrations đầy đủ

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.warning import Warning, WarningCreatedBy
from app.models.prediction import Prediction, RiskLevel
from app.models.notification import Notification, NotificationType
from app.models.event import Event, EventType, TargetAudience
from app.models.document import Document

__all__ = [
    "User", "UserRole",
    "Student",
    "Course",
    "Enrollment", "EnrollmentStatus",
    "Warning", "WarningCreatedBy",
    "Prediction", "RiskLevel",
    "Notification", "NotificationType",
    "Event", "EventType", "TargetAudience",
    "Document",
]
