from django import forms

from .models import Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = (
            "company_name",
            "job_title",
            "description",
            "required_skills",
            "minimum_cgpa",
            "maximum_backlogs",
            "location",
            "package",
            "deadline",
            "drive_date",
            "status",
        )
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "drive_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "required_skills": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_minimum_cgpa(self):
        minimum_cgpa = self.cleaned_data["minimum_cgpa"]
        if minimum_cgpa < 0 or minimum_cgpa > 10:
            raise forms.ValidationError("Minimum CGPA must be between 0 and 10.")
        return minimum_cgpa

    def clean_maximum_backlogs(self):
        maximum_backlogs = self.cleaned_data["maximum_backlogs"]
        if maximum_backlogs < 0:
            raise forms.ValidationError("Maximum backlogs cannot be negative.")
        return maximum_backlogs
