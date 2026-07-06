import django_filters
from .models import Animal


class AnimalFilter(django_filters.FilterSet):
    species = django_filters.CharFilter(field_name="species")
    breed = django_filters.CharFilter(field_name="breed", lookup_expr="icontains")
    size = django_filters.CharFilter(field_name="size")
    gender = django_filters.CharFilter(field_name="gender")
    energy_level = django_filters.CharFilter(field_name="energy_level")
    min_age_months = django_filters.NumberFilter(field_name="approximate_age_months", lookup_expr="gte")
    max_age_months = django_filters.NumberFilter(field_name="approximate_age_months", lookup_expr="lte")
    good_with_children = django_filters.BooleanFilter(field_name="good_with_children")
    good_with_dogs = django_filters.BooleanFilter(field_name="good_with_dogs")
    good_with_cats = django_filters.BooleanFilter(field_name="good_with_cats")
    city = django_filters.CharFilter(field_name="shelter__city", lookup_expr="icontains")
    state = django_filters.CharFilter(field_name="shelter__state", lookup_expr="iexact")
    shelter = django_filters.UUIDFilter(field_name="shelter__id")

    class Meta:
        model = Animal
        fields = [
            "species", "breed", "size", "gender", "energy_level",
            "good_with_children", "good_with_dogs", "good_with_cats",
            "city", "state", "shelter",
        ]
