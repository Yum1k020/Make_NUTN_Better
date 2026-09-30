"""Validate stored data before serialization; invalid server data must never become a 200."""

import math
import re
from datetime import date

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

CATEGORIES = ["general_core", "general_domain", "general_diverse", "college_required",
              "department_required", "department_elective", "free_elective"]


def nonempty(value):
    if not value.strip():
        raise ValidationError("Must not be blank")


def valid_date(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValidationError("Invalid date format")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValidationError("Invalid date") from error


def valid_time(value):
    if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
        raise ValidationError("Invalid time")


def text(**kwargs):
    return fields.String(required=True, validate=nonempty, **kwargs)


class Credits(fields.Float):
    def _deserialize(self, value, attr, data, **kwargs):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValidationError("Credits must be a finite nonnegative number")
        return value


class SemesterSchema(Schema):
    semester_id = text()
    academic_year = fields.Integer(required=True, strict=True, validate=validate.Range(min=1))
    term = fields.String(required=True, validate=validate.OneOf(["1", "2"]))
    starts_on = fields.String(required=True, validate=valid_date, metadata={"format": "date"})
    ends_on = fields.String(required=True, validate=valid_date, metadata={"format": "date"})
    timezone = fields.String(required=True, validate=validate.Equal("Asia/Taipei"))

    @validates_schema
    def chronology(self, data, **kwargs):
        if data["ends_on"] < data["starts_on"]:
            raise ValidationError("Semester ends before it starts")


class ClassificationSchema(Schema):
    rule_set_id = text()
    credit_category = fields.String(required=True, allow_none=True, validate=validate.OneOf(CATEGORIES))
    status = fields.String(required=True, validate=validate.OneOf(["classified", "unclassified"]))

    @validates_schema
    def consistency(self, data, **kwargs):
        if (data["status"] == "unclassified") != (data["credit_category"] is None):
            raise ValidationError("Classification status does not match category")


class CourseSchema(Schema):
    course_id = text()
    course_code = text(allow_none=True)
    name = text()
    credits = Credits(required=True)
    offering_department_id = text(allow_none=True)
    classification = fields.Nested(ClassificationSchema, required=True, allow_none=True)


class PrerequisiteSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf(["known", "none", "unknown"]))
    mode = fields.String(required=True, allow_none=True, validate=validate.OneOf(["all", "any"]))
    course_ids = fields.List(text(), required=True, allow_none=True)
    source = text(allow_none=True)

    @validates_schema
    def consistency(self, data, **kwargs):
        status, mode, ids = data["status"], data["mode"], data["course_ids"]
        if status == "known":
            if mode is None or not ids or len(ids) != len(set(ids)) or not data["source"]:
                raise ValidationError("Known prerequisites require IDs, mode and source")
        elif mode is not None or ids != ([] if status == "none" else None):
            raise ValidationError("Invalid none/unknown prerequisite representation")
        if status == "none" and not data["source"]:
            raise ValidationError("Confirmed absence requires a source")


class CourseDetailSchema(CourseSchema):
    prerequisites = fields.Nested(PrerequisiteSchema, required=True)


class MeetingSchema(Schema):
    meeting_id = text()
    weekday = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=7))
    start_time = fields.String(required=True, validate=valid_time)
    end_time = fields.String(required=True, validate=valid_time)
    campus_id = text(allow_none=True)
    location = fields.String(required=True, allow_none=True)

    @validates_schema
    def chronology(self, data, **kwargs):
        if data["end_time"] <= data["start_time"]:
            raise ValidationError("Meetings must end later on the same day")


class OfferingSchema(Schema):
    offering_id = text()
    course_id = text()
    course_name = text()
    semester_id = text()
    section_name = fields.String(required=True, allow_none=True)
    schedule_status = fields.String(required=True, validate=validate.OneOf(["scheduled", "unknown"]))
    class_meetings = fields.List(fields.Nested(MeetingSchema), required=True)

    @validates_schema
    def consistency(self, data, **kwargs):
        if (data["schedule_status"] == "scheduled") != bool(data["class_meetings"]):
            raise ValidationError("Schedule status does not match meetings")


class CountSchema(Schema):
    count = fields.Integer(required=True, strict=True, validate=validate.Range(min=0))


class CatalogListSchema(Schema):
    meta = fields.Nested(CountSchema, required=True)

    @validates_schema
    def count_matches(self, data, **kwargs):
        if data["meta"]["count"] != len(data["data"]):
            raise ValidationError("Count does not match list")


class SemesterListSchema(CatalogListSchema):
    data = fields.List(fields.Nested(SemesterSchema), required=True)


class CourseListSchema(CatalogListSchema):
    data = fields.List(fields.Nested(CourseSchema), required=True)


class OfferingListSchema(CatalogListSchema):
    data = fields.List(fields.Nested(OfferingSchema), required=True)


class CourseResponseSchema(Schema):
    data = fields.Nested(CourseDetailSchema, required=True)
