from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from .permissions import IsPetOwner, IsVet
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .decorators import role_required
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

# ------------------------------------------------------------------
# Session-based login -> role redirect
#
# Append this block to the bottom of myapp/views.py, and add this
# import near the top of that file:
#     from .decorators import role_required
#
# These are intentionally separate from the JWT/DRF views above (used
# by API clients). This flow is for the browser session — plain login
# form, Django session cookie, then redirect by role. The dashboard
# views below just confirm which branch was hit; swap the render()
# template argument for your real UI once redirection is verified.



def login_page(request):
    """
    GET  -> renders the login form
    POST -> authenticates, starts a session, redirects by role
    """
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard_redirect')
        error = 'Invalid username or password.'

    return render(request, 'myapp/login.html', {'error': error, 'page_title': 'Login'})


def logout_view(request):
    logout(request)
    return redirect('login_page')


@login_required(login_url='login_page')
def dashboard_redirect(request):
    """
    Single entry point after login. This is the actual redirection
    logic — everything else in this file is just there to render
    something visible so you can confirm each branch works.
    """
    user = request.user

    if user.is_superuser or user.is_staff:
        return redirect('admin:index')

    if user.is_vet:
        return redirect('vet_dashboard_page')

    return redirect('user_dashboard_page')


@role_required(User.Role.USER)
def user_dashboard_page(request):
    # Placeholder — replace this render() call with your real
    # dashboard template once you're satisfied redirection is correct.
    return render(request, 'myapp/dashboard_placeholder.html', {
        'page_title': 'User Dashboard',
        'role_label': 'Pet Owner',
    })


@role_required(User.Role.VET)
def vet_dashboard_page(request):
    return render(request, 'myapp/dashboard_placeholder.html', {
        'page_title': 'Vet Dashboard',
        'role_label': 'Veterinarian',
    })

@role_required(User.Role.PHARMACY)
def pharmacy_dashboard_page(request):
    return render(request, 'myapp/dashboard_placeholder.html', {
        'page_title': 'Pharmacy Dashboard',
        'role_label': 'Pharmacy',
    })
