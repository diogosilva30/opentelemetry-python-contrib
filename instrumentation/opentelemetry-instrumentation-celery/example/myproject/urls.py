from django.http import JsonResponse
from django.urls import path

from myproject.tasks import add, fail_task


def trigger_add(request):
    result = add.delay(4, 6)
    return JsonResponse({"task_id": result.id, "status": "submitted"})


def trigger_fail(request):
    result = fail_task.delay()
    return JsonResponse({"task_id": result.id, "status": "submitted"})


urlpatterns = [
    path("add/", trigger_add),
    path("fail/", trigger_fail),
]
