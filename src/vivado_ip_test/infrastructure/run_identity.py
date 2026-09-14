from datetime import datetime
from uuid import uuid4


def create_run_id(moment: datetime | None = None) -> str:
    local_time = (moment or datetime.now()).astimezone()
    return local_time.strftime("%Y-%m-%d_%H-%M-%S_UTC%z_") + uuid4().hex[:8]
