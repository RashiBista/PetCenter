from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from .permissions import IsPetOwner, IsVet
from .serializers import (
    LoginSerializer,
    UserPublicSerializer,
    UserRegisterSerializer,
    VetRegisterSerializer,
)

User = get_user_model()


def _tokens_for_user(user):
    """Build a JWT pair with the user's role embedded as a custom claim."""
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    refresh['username'] = user.username
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserRegisterView(generics.CreateAPIView):
    """POST /api/auth/register/user/ — registers a pet-owner account."""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.save()
            tokens = _tokens_for_user(user)
            return Response(
                {
                    'message': 'User registered successfully.',
                    'user': UserPublicSerializer(user).data,
                    **tokens,
                },
                status=201,
            )
        except IntegrityError as e:
            if 'email' in str(e):
                return Response(
                    {'email': ['A user with this email already exists.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif 'username' in str(e):
                return Response(
                    {'username': ['A user with this username already exists.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise


class VetRegisterView(generics.CreateAPIView):
    """POST /api/auth/register/vet/ — registers a veterinarian account."""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = VetRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.save()
            tokens = _tokens_for_user(user)
            return Response(
                {
                    'message': 'Vet registered successfully.',
                    'user': UserPublicSerializer(user).data,
                    **tokens,
                },
                status=201,
            )
        except IntegrityError as e:
            if 'email' in str(e):
                return Response(
                    {'email': ['A user with this email already exists.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif 'username' in str(e):
                return Response(
                    {'username': ['A user with this username already exists.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise


class LoginView(generics.GenericAPIView):
    """
    POST /api/auth/login/ — single login endpoint shared by both roles.
    The response includes `role` so the client can route to the correct
    dashboard/UI without needing separate login endpoints per role.
    """
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response({'message': 'Invalid credentials'}, status=401)

        tokens = _tokens_for_user(user)
        return Response({
            'message': 'Login successful',
            'user': UserPublicSerializer(user).data,
            **tokens,
        })


class DashboardView(APIView):
    """
    GET /api/auth/dashboard/ — generic dashboard, available to any
    authenticated user regardless of role.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return Response({
            'message': 'Welcome to the dashboard',
            'user': UserPublicSerializer(request.user).data,
        }, status=200)


class UserDashboardView(APIView):
    """GET /api/auth/dashboard/user/ — accessible only to pet-owner accounts."""
    permission_classes = (IsAuthenticated, IsPetOwner)

    def get(self, request, *args, **kwargs):
        return Response({
            'message': 'Welcome to your pet-owner dashboard',
            'user': UserPublicSerializer(request.user).data,
        }, status=200)


class VetDashboardView(APIView):
    """GET /api/auth/dashboard/vet/ — accessible only to vet accounts."""
    permission_classes = (IsAuthenticated, IsVet)

    def get(self, request, *args, **kwargs):
        return Response({
            'message': 'Welcome to your veterinarian dashboard',
            'user': UserPublicSerializer(request.user).data,
        }, status=200)
class UserSearchView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})

        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(pets__name__icontains=query)
        ).exclude(id=request.user.id).distinct().prefetch_related('pets')[:10]

        results = []
        for user in users:
            results.append({
                'id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip(),
                'role': user.role,
                'pets': list(user.pets.values('id', 'name', 'species')),
            })
        return Response({'results': results})

