"""The two public forms: a question for an expert, and a farm-visit request (D41).

One ModelForm serves both; the kind decides which fields appear and which are
required. The model's own clean() checks the same rules, so a request cannot
be stored without them from anywhere else either.

`website` is the honeypot (D12): a field people never see and never fill in.
"""
from django import forms

from apps.catalog.models import Crop

from .models import MESSAGE_MAX_LENGTH, ConsultationRequest

Kind = ConsultationRequest.Kind

CONTROL = (
    "block min-h-12 w-full rounded-lg border border-stone-200 bg-white px-4 py-2 "
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-800"
)


class TelInput(forms.TextInput):
    """type="tel": phones show the number keypad. (Django writes `type` itself, so it cannot go in attrs.)"""

    input_type = "tel"


class ConsultationForm(forms.ModelForm):
    website = forms.CharField(required=False)  # the honeypot

    class Meta:
        model = ConsultationRequest
        fields = ["name", "phone", "crop", "message", "village_or_address"]
        labels = {
            "name": "نام و نام خانوادگی",
            "phone": "شماره موبایل",
            "crop": "محصول یا گیاه مورد نظر",
            "message": "پرسش شما",
            "village_or_address": "روستا یا نشانی مزرعه",
        }

    def __init__(self, *args, kind: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.kind = kind  # model.clean() needs it to know what is required
        self.fields["crop"].queryset = Crop.objects.all()
        self.fields["crop"].empty_label = "انتخاب کنید"

        if kind == Kind.QUESTION:
            del self.fields["village_or_address"]
            self.fields["message"].required = True
        else:
            self.fields["village_or_address"].required = True
            self.fields["message"].label = "توضیحات (مثلاً نوع محصول و مشکل)"

        self.fields["name"].widget.attrs.update(autocomplete="name", maxlength=100)
        self.fields["phone"].widget = TelInput(
            attrs={"inputmode": "numeric", "autocomplete": "tel", "dir": "ltr", "maxlength": 25}
        )
        self.fields["message"].widget = forms.Textarea(attrs={"rows": 5, "maxlength": MESSAGE_MAX_LENGTH})
        if "village_or_address" in self.fields:
            self.fields["village_or_address"].widget.attrs.update(maxlength=255)
        for field in self.fields.values():
            if field is not self.fields["website"]:
                field.widget.attrs["class"] = CONTROL
        self.fields["website"].widget.attrs.update(tabindex="-1", autocomplete="off")
