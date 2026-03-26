# add routers from the folder here with the naming convention SECTION_router
# routers should be called 'router' in their respective files

from .test_endpoints import router as test_router
from .sample_endpoints import router as sample_router
from .chat_endpoints import router as chat_router
from .dynamic_data_info_endpoints import router as dynamic_data_router