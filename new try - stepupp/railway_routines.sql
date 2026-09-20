-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: altaria.proxy.rlwy.net    Database: railway
-- ------------------------------------------------------
-- Server version	9.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Temporary view structure for view `student_rank_view`
--

DROP TABLE IF EXISTS `student_rank_view`;
/*!50001 DROP VIEW IF EXISTS `student_rank_view`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `student_rank_view` AS SELECT 
 1 AS `studentid`,
 1 AS `regno`,
 1 AS `name`,
 1 AS `department`,
 1 AS `year`,
 1 AS `marks_percentage`,
 1 AS `attendance_percentage`,
 1 AS `department_rank`*/;
SET character_set_client = @saved_cs_client;

--
-- Final view structure for view `student_rank_view`
--

/*!50001 DROP VIEW IF EXISTS `student_rank_view`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`%` SQL SECURITY DEFINER */
/*!50001 VIEW `student_rank_view` AS select `s`.`studentid` AS `studentid`,`s`.`regno` AS `regno`,`s`.`name` AS `name`,`s`.`department` AS `department`,`s`.`year` AS `year`,coalesce(`m`.`avg_pct`,0) AS `marks_percentage`,coalesce(`a`.`att_pct`,0) AS `attendance_percentage`,rank() OVER (PARTITION BY `s`.`department` ORDER BY coalesce(`m`.`avg_pct`,0) desc )  AS `department_rank` from ((`students` `s` left join (select `internal_marks`.`student_id` AS `student_id`,round(((sum(`internal_marks`.`marks_obtained`) / nullif(sum(`internal_marks`.`max_marks`),0)) * 100),2) AS `avg_pct` from `internal_marks` group by `internal_marks`.`student_id`) `m` on((`m`.`student_id` = `s`.`studentid`))) left join (select `attendance`.`student_id` AS `student_id`,round(((sum((`attendance`.`status` = 'Present')) / count(0)) * 100),2) AS `att_pct` from `attendance` group by `attendance`.`student_id`) `a` on((`a`.`student_id` = `s`.`studentid`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Dumping routines for database 'railway'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-30 13:01:14
