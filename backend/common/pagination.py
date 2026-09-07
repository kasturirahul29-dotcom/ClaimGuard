from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Default pagination for all list endpoints.
    Returns 20 items per page. Clients can override with ?page_size=N
    up to a maximum of 100.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
