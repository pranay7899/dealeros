from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Location
from .service import get_disagreements_for_org


class DisagreementsView(APIView):
    """
    GET /api/disagreements/?org=ORG-A&reason=VALUE_MISMATCH&sort=-value
    Returns tenant-scoped reconciliation disagreements.
    """

    def get(self, request):
        org = request.query_params.get("org")
        if not org:
            return Response(
                {"error": "Query parameter 'org' is required (e.g. ?org=ORG-A)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = org.strip().upper()
        # Verify tenant exists
        if not Location.objects.filter(org_id=org).exists():
            return Response(
                {"error": f"Organization '{org}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reason = request.query_params.get("reason")
        sort = request.query_params.get("sort")

        disagreements = get_disagreements_for_org(
            org_id=org,
            reason_filter=reason,
            sort_by=sort,
        )

        return Response(disagreements, status=status.HTTP_200_OK)


class OrgsListView(APIView):
    """
    GET /api/orgs/
    Returns list of available tenant organizations.
    """

    def get(self, request):
        orgs = list(
            Location.objects.values_list("org_id", flat=True)
            .distinct()
            .order_by("org_id")
        )
        return Response(orgs, status=status.HTTP_200_OK)


class ReasonsListView(APIView):
    """
    GET /api/reasons/
    Returns list of supported disagreement reason categories.
    """

    def get(self, request):
        reasons = [
            {"code": "MISSING_IN_B", "label": "Missing in System B"},
            {"code": "ORPHAN_IN_B", "label": "Orphan in System B"},
            {"code": "DUPLICATE_IN_B", "label": "Duplicate in System B"},
            {"code": "VALUE_MISMATCH", "label": "Value Mismatch"},
            {"code": "LOCATION_MISMATCH", "label": "Location Mismatch"},
            {"code": "DATE_MISMATCH", "label": "Date Mismatch"},
        ]
        return Response(reasons, status=status.HTTP_200_OK)
