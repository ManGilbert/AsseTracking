from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.generators import SchemaGenerator

@api_view(["GET"])
@permission_classes([AllowAny])
def api_index(request):
	"""Return a simple list of available API endpoint paths.

	This view uses drf-spectacular's SchemaGenerator to extract the
	registered OpenAPI paths and returns them as a JSON response. It is
	intentionally open to unauthenticated users so the project API index
	can be browsed at /api/.
	"""
	try:
		generator = SchemaGenerator()
		schema = generator.get_schema(request=request, public=True)
		paths = sorted(schema.get("paths", {}).keys()) if schema else []
	except Exception:
		paths = []
	return Response({"endpoints": paths})
