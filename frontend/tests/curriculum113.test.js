import test from "node:test";
import assert from "node:assert/strict";
import {
  graduationRequirements113,
  professionalElectives113,
  programs113,
  requiredCourses113,
} from "../src/data/curriculum113.js";

test("113 curriculum required courses match the documented 70-credit total", () => {
  assert.equal(requiredCourses113.length, 25);
  assert.equal(
    requiredCourses113.reduce((sum, course) => sum + course.credits, 0),
    graduationRequirements113.departmentRequiredCredits,
  );
  assert.equal(
    new Set(requiredCourses113.map((course) => course.code)).size,
    25,
  );
});

test("113 curriculum exposes the documented graduation thresholds", () => {
  assert.deepEqual(
    {
      total: graduationRequirements113.minimumTotalCredits,
      general: graduationRequirements113.generalEducationCredits,
      college: graduationRequirements113.collegeCoreCredits,
      department: graduationRequirements113.minimumDepartmentCredits,
      free: graduationRequirements113.freeElectiveCredits,
      lectures: graduationRequirements113.requiredLectureCount,
      programs: graduationRequirements113.minimumCompletedPrograms,
    },
    {
      total: 134,
      general: 28,
      college: 4,
      department: 82,
      free: 20,
      lectures: 10,
      programs: 2,
    },
  );
});

test("113 curriculum catalog and program map stay internally consistent", () => {
  assert.equal(professionalElectives113.length, 35);
  assert.deepEqual(
    programs113.map((program) => program.courses.length),
    [11, 10, 10],
  );
  assert.ok(
    programs113.every(
      (program) =>
        program.courses.length >= graduationRequirements113.coursesPerProgram,
    ),
  );
});
