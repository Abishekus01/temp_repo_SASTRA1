from typehints import *

def create_triggers(db_connector: Connection, cursor: Cursor):
	cursor.execute("""CREATE PROCEDURE IF NOT EXISTS `validate_join_year`
				   (IN `year` SMALLINT UNSIGNED)
				   IF `year` > YEAR(CURDATE())
				   	THEN SIGNAL SQLSTATE '45000'
				   	SET MESSAGE_TEXT='Invalid year: Join Year cannot be greater than the current year';
				   END IF;
	""")
	cursor.execute("""CREATE PROCEDURE IF NOT EXISTS `department_exists`
				   (IN `campus_id` TINYINT UNSIGNED, IN `department` VARCHAR(40))
				   IF NOT EXISTS (
					SELECT 1
					FROM `campus_departments` `CD`
					WHERE `CD`.`department`=`department`
					AND `CD`.`campus_id`=`campus_id`
					LIMIT 1
				   )
				   	THEN SIGNAL SQLSTATE '45000'
				   	SET MESSAGE_TEXT='Value Error: Department does not exist in this Campus';
				   END IF;
	""")
	cursor.execute("""CREATE PROCEDURE IF NOT EXISTS `dept_class`
				   (IN `department` VARCHAR(40), IN `class_id` MEDIUMINT UNSIGNED)
				   IF NOT EXISTS (
					SELECT 1
					FROM `school_departments` `SD`
					JOIN `buildings`
					ON `SD`.`school_id`=`buildings`.`school_id`
					JOIN `classes`
					ON `buildings`.`id`=`classes`.`building_id`
					AND `SD`.`department`=`department`
					AND `classes`.`id`=`class_id`
					LIMIT 1
				   )
					THEN SIGNAL SQLSTATE '45000'
					SET MESSAGE_TEXT='Invalid Class: Class does not belong to the given Department';
				   END IF;
	""")
	cursor.execute("""CREATE PROCEDURE IF NOT EXISTS `section_campus_class`
				   (IN `section_id` MEDIUMINT UNSIGNED,
				   IN `class_id` MEDIUMINT UNSIGNED)
				   IF NOT EXISTS (
				   	SELECT 1
					FROM `sections`
					JOIN `classes`
					ON `sections`.`id`=`section_id`
					AND`classes`.`id`=`class_id`
					JOIN `campus_buildings` `CB`
					ON `CB`.`campus_id`=`sections`.`campus_id`
					AND `CB`.`building_id`=`classes`.`building_id`
					LIMIT 1
				   )
				   	THEN SIGNAL SQLSTATE '45000'
				   	SET MESSAGE_TEXT='Invalid Section: Class is not in the same Campus as Section';
				   END IF;
	""")
	cursor.execute("""CREATE PROCEDURE IF NOT EXISTS `section_campus_student`
				   (IN `section_id` MEDIUMINT UNSIGNED,
				   IN `student_id` INT UNSIGNED)
				   IF NOT EXISTS (
					 SELECT 1
					 FROM `sections`
					 JOIN `students`
					 ON `sections`.`id`=`section_id`
					 AND `students`.`id`=`student_id`
					 AND `sections`.`campus_id`=`students`.`campus_id`
					 LIMIT 1
				   )
					 THEN SIGNAL SQLSTATE '45000'
					 SET MESSAGE_TEXT='Invalid Section: Student is not in the same Campus as Section';
				   END IF;
	""")
	cursor.execute("""CREATE PROCEDURE IF NOT EXISTS `section_student_programme`
				   (IN `section_id` MEDIUMINT UNSIGNED,
				   IN `student_id` INT UNSIGNED)
				   IF NOT (
					 SELECT 1
					 FROM `sections`
					 JOIN `students`
					 ON `sections`.`id`=`section_id`
					 AND `students`.`id`=`student_id`
					 JOIN `programmes`
					 ON `sections`.`degree`=`programmes`.`degree`
					 AND (
						`sections`.`stream` IS NULL
						OR `sections`.`stream`=`programmes`.`stream`
					 )
					 AND `students`.`programme_id`=`programmes`.`id`
					 LIMIT 1
				   )
					 THEN SIGNAL SQLSTATE '45000'
					 SET MESSAGE_TEXT='Invalid Student ID in Section: Student is not in the same Programme as Section';
				   END IF;
	""")
	cursor.execute("""CREATE FUNCTION IF NOT EXISTS `get_is_lab`(`class_id` MEDIUMINT UNSIGNED)
				   RETURNS BOOLEAN
				   NOT DETERMINISTIC
				   READS SQL DATA
					RETURN (SELECT `is_lab`
							FROM `classes`
							WHERE `id`=`class_id`);
	""")
	cursor.execute("""CREATE FUNCTION IF NOT EXISTS `section_has_course`
				   (`section_id` MEDIUMINT UNSIGNED, `course_code` VARCHAR(10))
				   RETURNS BOOLEAN
				   NOT DETERMINISTIC
				   READS SQL DATA
					RETURN EXISTS (
							SELECT 1
							FROM `sections`
							JOIN `programmes`
							ON `sections`.`degree`=`programmes`.`degree`
							AND (
								`sections`.`stream` is NULL
								OR `sections`.`stream`=`programmes`.`stream`
							)
							AND `sections`.`id`=`section_id`
							JOIN `programme_courses` `PC`
							ON `programmes`.`id`=`PC`.`programme_id`
							AND `PC`.`course_code`=`course_code`
							LIMIT 1
					);
	""")
	cursor.execute("""CREATE FUNCTION IF NOT EXISTS `get_is_elective`(`course_code` VARCHAR(10))
				   RETURNS BOOLEAN
				   NOT DETERMINISTIC
				   READS SQL DATA
					RETURN (SELECT `is_elective`
							FROM `courses`
							WHERE `code`=`course_code`);
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `campus_has_programme_department`
				   BEFORE INSERT ON `campus_programmes`
				   FOR EACH ROW
				   BEGIN
					DECLARE `dept` VARCHAR(40);
					SELECT `streams`.`department` INTO `dept`
					FROM `programmes`
					JOIN `streams`
					ON `streams`.`name`=`programmes`.`stream`
					AND NEW.`programme_id`=`id`;

					CALL `department_exists`(NEW.`campus_id`, `dept`);
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `no_of_rooms_dept_insert`
				   BEFORE INSERT ON `classes`
				   FOR EACH ROW
				   BEGIN
					DECLARE `room_count` INT;
					SELECT COUNT(*) INTO `room_count`
					FROM `classes`
					WHERE `building_id`=NEW.`building_id`;
					IF `room_count` >= (SELECT `rooms`
									  FROM `buildings`
									  WHERE `id`=NEW.`building_id`)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Limit Exceeded: Number of classrooms cannot exceed the number of rooms in the building';
					END IF;
					IF NEW.`is_lab` AND NEW.`department` IS NULL
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Missing department: Lab classes must have a department';
						CALL `dept_class`(NEW.`department`, NEW.`id`);
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `no_of_rooms_dept_update`
				   BEFORE UPDATE ON `classes`
				   FOR EACH ROW
				   BEGIN
					DECLARE `room_count` INT;
					SELECT COUNT(*) INTO `room_count` 
					FROM `classes`
					WHERE `building_id`=NEW.`building_id`;
					IF `room_count` >= (SELECT `rooms`
									  FROM `buildings`
									  WHERE `id`=NEW.`building_id`)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Limit Exceeded: Number of classrooms cannot exceed the number of rooms in the building';
					END IF;
					IF NEW.`is_lab` AND NEW.`department` IS NULL
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Missing Department: Lab classes must have a department';
						CALL `dept_class`(NEW.`department`, NEW.`id`);
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `section_yr_programme_chk_insert`
				  BEFORE INSERT ON `sections`
				  FOR EACH ROW
				  BEGIN
					DECLARE `degree_duration` TINYINT UNSIGNED;
				    IF NOT EXISTS (
						SELECT 1
						FROM `campus_programmes` `CP`
						JOIN `programmes`
						ON `CP`.`programme_id`=`programmes`.`id`
						AND `CP`.`campus_id`=NEW.`campus_id`
						AND ((NEW.`stream` IS NULL AND `programmes`.`degree`=NEW.`degree`)
							OR 
							(NEW.`stream` IS NOT NULL AND `programmes`.`degree`=NEW.`degree`
							AND `programmes`.`stream`=NEW.`stream`))
						LIMIT 1
					)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid Programme: Must also be in the same Campus';
					END IF;

					SELECT `duration` INTO `degree_duration`
					FROM `degrees`
					WHERE `name`=NEW.`degree`;
					IF NEW.`year` <= 0 OR NEW.`year` > `degree_duration`
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid Year: Must be in the range 1 and degree-duration';
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `section_yr_programme_chk_update`
				  BEFORE UPDATE ON `sections`
				  FOR EACH ROW
				  BEGIN
					DECLARE `degree_duration` TINYINT UNSIGNED;
				    IF NOT EXISTS (
						SELECT 1
						FROM `campus_programmes` `CP`
						JOIN `programmes`
						ON `CP`.`programme_id`=`programmes`.`id`
						AND `CP`.`campus_id`=NEW.`campus_id`
						AND ((NEW.`stream` IS NULL AND `programmes`.`degree`=NEW.`degree`)
							OR 
							(NEW.`stream` IS NOT NULL AND `programmes`.`degree`=NEW.`degree`
							AND `programmes`.`stream`=NEW.`stream`))
						LIMIT 1
					)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid Programme: Must also be in the same Campus';
					END IF;

					SELECT `duration` INTO `degree_duration`
					FROM `degrees`
					WHERE `name`=NEW.`degree`;
					IF NEW.`year` <= 0 OR NEW.`year` > `degree_duration`
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid Year: Must be in the range 1 and degree-duration';
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `faculties_join_yr_dept_chk_insert`
				   BEFORE INSERT ON `faculties`
				   FOR EACH ROW
				   BEGIN
					CALL `validate_join_year`(NEW.`join_year`);
					CALL `department_exists`(NEW.`campus_id`, NEW.`department`);
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `faculties_join_yr_dept_chk_update`
				   BEFORE UPDATE ON `faculties`
				   FOR EACH ROW
				   BEGIN
					CALL `validate_join_year`(NEW.`join_year`);
					CALL `department_exists`(NEW.`campus_id`, NEW.`department`);
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `students_join_yr_chk_roll_incr_insert`
				   BEFORE INSERT ON `students`
				   FOR EACH ROW
				   BEGIN
					DECLARE `max_roll` SMALLINT UNSIGNED;
					CALL `validate_join_year`(NEW.`join_year`);

					IF NEW.`roll_no` IS NULL THEN
						SELECT IFNULL(MAX(`roll_no`), 0) INTO `max_roll`
						FROM `students`
						WHERE `campus_id`=NEW.`campus_id`
						AND `join_year`=NEW.`join_year`
						AND `programme_id`=NEW.`programme_id`;

						SET NEW.`roll_no`=`max_roll`+1;
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `students_join_yr_chk_update`
				   BEFORE UPDATE ON `students`
				   FOR EACH ROW
					CALL `validate_join_year`(NEW.`join_year`);
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `section_class_same_campus_not_lab_insert`
				   BEFORE INSERT ON `section_class`
				   FOR EACH ROW
				   BEGIN
				   	CALL `section_campus_class`(NEW.`section_id`, NEW.`class_id`);
					IF `get_is_lab`(NEW.`class_id`)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid class: Class can not be lab';
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `section_class_same_campus_not_lab_update`
				   BEFORE UPDATE ON `section_class`
				   FOR EACH ROW
				   BEGIN
				   	CALL `section_campus_class`(NEW.`section_id`, NEW.`class_id`);
					IF `get_is_lab`(NEW.`class_id`)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid class: Class can not be lab';
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `section_student_capacity_same_campus_programme_insert`
				   BEFORE INSERT ON `section_students`
				   FOR EACH ROW
				   BEGIN
					CALL `section_campus_student`(NEW.`section_id`, NEW.`student_id`);
					CALL `section_student_programme`(NEW.`section_id`, NEW.`student_id`);
					IF (
						SELECT COUNT(*)
						FROM `section_students`
						WHERE `section_students`.`section_id`=NEW.`section_id`
					) >= (
						SELECT `classes`.`capacity`
						FROM `section_class`
						JOIN `classes`
						ON `section_class`.`class_id`=`classes`.id
						WHERE `section_class`.`section_id`=NEW.`section_id`
					)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Section Capacity Exceeded: Cannot add more students to this section';
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `section_student_same_campus_programme_update`
				   BEFORE UPDATE ON `section_students`
				   FOR EACH ROW
				   BEGIN
					CALL `section_campus_student`(NEW.`section_id`, NEW.`student_id`);
					CALL `section_student_programme`(NEW.`section_id`, NEW.`student_id`);
				   END;
	""")		
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `faculty_course_section_insert`
				   BEFORE INSERT ON `faculty_section_course`
				   FOR EACH ROW
					IF NOT `section_has_course`(NEW.`section_id`, NEW.`course_code`)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid Course: Course not found in given Section';
					END IF;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `faculty_course_section_update`
				   BEFORE UPDATE ON `faculty_section_course`
				   FOR EACH ROW
					IF NOT `section_has_course`(NEW.`section_id`, NEW.`course_code`)
						THEN SIGNAL SQLSTATE '45000'
						SET MESSAGE_TEXT='Invalid Course: Course not found in given Section';
					END IF;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `student_elective_insert`
				   BEFORE INSERT ON `student_electives`
				   FOR EACH ROW
					IF NOT EXISTS (
						SELECT 1
						FROM `students`
						JOIN `programme_courses` `PC`
						ON `students`.`programme_id`=`PC`.`programme_id`
						AND `PC`.`course_code`=NEW.`course_code`
						AND `get_is_elective`(NEW.`course_code`)
						AND `students`.`id`=NEW.`student_id`
						LIMIT 1
					)
						THEN SIGNAL SQLSTATE '45000'
				   		SET MESSAGE_TEXT='Invalid Course: Course is not valid elective for the Student''s programme';
				   	END IF;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `student_elective_update`
				   BEFORE UPDATE ON `student_electives`
				   FOR EACH ROW
					IF NOT EXISTS (
						SELECT 1
						FROM `students`
						JOIN `programme_courses` `PC`
						ON `students`.`programme_id`=`PC`.`programme_id`
						AND `PC`.`course_code`=NEW.`course_code`
						AND `get_is_elective`(NEW.`course_code`)
						AND `students`.`id`=NEW.`student_id`
						LIMIT 1
					)
						THEN SIGNAL SQLSTATE '45000'
				   		SET MESSAGE_TEXT='Invalid Course: Course is not valid elective for the Student''s programme';
				   	END IF;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `timetable_same_fac_class_full_insert`
				   BEFORE INSERT ON `timetables`
				   FOR EACH ROW
				   BEGIN
					DECLARE `class_count` TINYINT UNSIGNED;
					DECLARE `new_faculty_id`, `new_section_id`, `no_of_students` MEDIUMINT UNSIGNED;

					SELECT `faculty_id`, `section_id`
					INTO `new_faculty_id`, `new_section_id`
					FROM `faculty_section_course`
					WHERE `id`=NEW.`faculty_section_course_id`;

					SELECT COUNT(*) INTO `class_count`
					FROM `timetables`
					JOIN `faculty_section_course` `FSC`
					ON `FSC`.`id`=`timetables`.`faculty_section_course_id`
					WHERE `FSC`.`faculty_id`=`new_faculty_id`
					AND `FSC`.`section_id`=`new_section_id`
					AND `timetables`.`day`=NEW.`day`;

					IF `class_count` >= 3
						THEN SIGNAL SQLSTATE '45000'
				   		SET MESSAGE_TEXT='Same faculty cannot take more than 3 class for the same section on the same day';
					END IF;

					IF EXISTS (
						SELECT 1
						FROM `timetables`
						JOIN `faculty_section_course` `FSC1`
						ON `FSC1`.`id`=`faculty_section_course_id`
						JOIN `faculty_section_course` `FSC2`
						ON `FSC2`.`id`=NEW.`faculty_section_course_id`
						AND `FSC1`.`faculty_id`=`FSC2`.`faculty_id`
						AND `day`=NEW.`day`
						AND `period_id`=NEW.`period_id`
						LIMIT 1
					)
						THEN SIGNAL SQLSTATE '45000'
				   		SET MESSAGE_TEXT='Same faculty cannot take more than one class at the same time';
					END IF;
				   END;
	""")
	cursor.execute("""CREATE TRIGGER IF NOT EXISTS `timetable_same_fac_class_full_update`
				   BEFORE UPDATE ON `timetables`
				   FOR EACH ROW
				   BEGIN
					DECLARE `class_count` TINYINT UNSIGNED;
					DECLARE `new_faculty_id`, `new_section_id` MEDIUMINT UNSIGNED;

					SELECT `faculty_id`, `section_id`
					INTO `new_faculty_id`, `new_section_id`
					FROM `faculty_section_course`
					WHERE `id`=NEW.`faculty_section_course_id`;

					SELECT COUNT(*) INTO `class_count`
					FROM `timetables`
					JOIN `faculty_section_course` `FSC`
					ON `FSC`.`id`=`timetables`.`faculty_section_course_id`
					WHERE `FSC`.`faculty_id`=`new_faculty_id`
					AND `FSC`.`section_id`=`new_section_id`
					AND `timetables`.`day`=NEW.`day`;

					IF `class_count` >= 3
						THEN SIGNAL SQLSTATE '45000'
				   		SET MESSAGE_TEXT='Same faculty cannot take more than 3 class for the same section on the same day';
					END IF;

					IF EXISTS (
						SELECT 1
						FROM `timetables`
						JOIN `faculty_section_course` `FSC1`
						ON `FSC1`.`id`=`faculty_section_course_id`
						JOIN `faculty_section_course` `FSC2`
						ON `FSC2`.`id`=NEW.`faculty_section_course_id`
						AND `FSC1`.`faculty_id`=`FSC2`.`faculty_id`
						AND `day`=NEW.`day`
						AND `period_id`=NEW.`period_id`
						LIMIT 1
					)
						THEN SIGNAL SQLSTATE '45000'
				   		SET MESSAGE_TEXT='Same faculty cannot take more than one class at the same time';
					END IF;
				   END;
	""")
	db_connector.commit()
# Trigger that a section can have atmost 2 labs (except electives) on the same day