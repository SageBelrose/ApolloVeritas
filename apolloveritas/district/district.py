from __future__ import annotations
from typing import List, Union, Dict
from pathlib import Path
import csv

from apolloveritas.google import GoogleUser, GoogleGroup, GoogleService
from apolloveritas.ldap import LdapUser, LdapGroup, LdapDirectory

"""
This class is an abstraction of the idea of districts, schools, students, staff, etc.
It allows for rapid high-level coordination between data sources by calling methods within other classes.
That said, because this caches a LOT of data in memory, the initialization can take quite some time.
"""


class District:

    def __init__(self):
        self.name = 'School District'  # TODO: Load from conf
        self.student_csv = self.load_student_csv()
        self.ldap = LdapDirectory()
        self.google_service = GoogleService()
        self.schools: List[School] = self.get_all_schools()
        self.students: List[Student] = self.get_all_students()
        self.staff: List[Staff] = self.get_all_staff()

    def load_student_csv(self, csv_file_path: Path = Path('student_export.csv')) -> List[Dict]:
        """
        Reads the student information csv specified in configuration file into memory.
        It expects to find a file called student_export.csv that contains the following columns:
        "StudentID","FirstName","MiddleName","LastName","Grade","SchoolID","Enrolled","District Relationship"
        Students not included in the student_export csv are will have their accounts disabled.
        Disabled users have their groups removed to keep group membership clean.
        Returns:
            A dictionary of key:value pairs from the student information csv file.
        """
        # TODO: build ingest/transfer mechanism for CSV
        with open(csv_file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            student_csv_values = [row for row in reader]
        return student_csv_values

    def get_all_schools(self) -> List[School]:
        """
        Queries the configured source of truth for a list of schools and
        initializes all school data.
        Returns:
            A list of School instances.
        """
        return []

    def get_all_students(self) -> List[Student]:
        """
        Queries the configured source of truth for what students should exist,
        as well as current created accounts, and loads data about all students known both past and present.
        Returns:
            A list of all students with objects for any existing accounts, as well as status information.
        """
        return []

    def get_all_staff(self) -> List[Staff]:
        """
        Queries the configured source of truth for what staff should exist,
        as well as currently existing staff accounts, and caches data.
        Returns:
            A list of all current and past known staff, with objects for accounts, and status information.
        """
        return []


class School:

    def __init__(self):
        pass


class Grade:

    def __init__(self, school, name):
        self.school = school
        self.name = name
        self.ordinal = Grade.make_ordinal(self.name)
        self.students: List[LdapUser] = self.get_all_students()
        self.teachers: List[LdapUser] = self.get_all_teachers()

    def get_all_students(self):
        students = []
        for user in self.school.students:
            if user.department == self.name:  # TODO: allow different source of truth for grade
                students.append(user)
        return students

    def get_all_teachers(self):
        teachers = []
        for user in self.school.allStaff:
            if user.department == self.name:  # TODO: allow different source of truth for grade
                teachers.append(user)
        return teachers

    @staticmethod
    def make_ordinal(n):
        """
        Convert an integer into its ordinal representation::

            make_ordinal(0)   => '0th'
            make_ordinal(3)   => '3rd'
            make_ordinal(122) => '122nd'
            make_ordinal(213) => '213th'
        """
        if n == '0':
            return "Kindergarten"
        if n == '-1':
            return "Preschool"
        try:
            n = int(n)
        except ValueError as e:
            if n.lower() == "k":
                return "Kindergarten"
            elif n.lower() == 'pk':
                return "Preschool"
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        if n > 0:
            return str(n) + suffix + "Grade"
        else:
            return str(n) + suffix


class Student:
    def __init__(self, student_csv_dict):
        self.student_id = student_csv_dict.get('StudentID')
        self.first_name = student_csv_dict.get('FirstName')
        self.middle_name = student_csv_dict.get('MiddleName')
        self.last_name = student_csv_dict.get("LastName")
        self.grade = student_csv_dict.get('Grade')
        self.school_id = student_csv_dict.get('SchoolID')
        self.enrolled: bool = True if student_csv_dict.get('Enrolled') else False
        # District Relationship is a set of status codes used by some districts, such as those in OHIO, to indicate
        # which students are a physical butt in a seat in their classrooms, versus students that live in one district
        # but attend school somewhere else.
        self.district_relationship = student_csv_dict.get('DistrictRelationship')

class Staff:

    def __init__(self):
        pass
