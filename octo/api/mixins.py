
from rest_framework.decorators import detail_route
from rest_framework.response import Response

# from memes import services
# from memes.api.serializers import MemesAuthorSerializer, MemesUsersLikesSerializer, MemesUsersCommentsSerializer
#
# import logging
# log = logging.getLogger("core.corelogger")
#
#
# class PatternsMixin:
#
#     @detail_route(methods=['POST'])
#     def like(self, request, pk=None):
#         obj = self.get_object()
#         services.Likes.like_meme(obj, request.user)
#         likes = services.Likes.all_likes(obj)
#         return Response({'likes': len(likes)})
#
#     @detail_route(methods=['GET'])
#     def dislikes(self, request, pk=None):
#         obj = self.get_object()
#         fans = services.Dislikes.all_dislikes(obj)
#         serializer = MemesUsersLikesSerializer(fans, many=True)
#         return Response(serializer.data)
#
#
# class TKUPackageMixin:
#
#     @detail_route(methods=['POST'])
#     def comment(self, request, pk=None):
#         obj = self.get_object()
#         services.Comments.leave_comment(obj, request.user, comment=request.GET.get('comment'))
#         return Response()
#
#     @detail_route(methods=['GET'])
#     def comments(self, request, pk=None):
#         log.debug("comments -> request: %s", request)
#
#         obj = self.get_object()
#         comments = services.Comments.get_all_comments(obj)
#         serializer = MemesUsersCommentsSerializer(comments, many=True)
#         return Response(serializer.data)