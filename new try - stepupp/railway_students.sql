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
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `studentid` int NOT NULL,
  `regno` varchar(20) DEFAULT NULL,
  `name` varchar(60) NOT NULL,
  `department` varchar(20) NOT NULL,
  `year` varchar(20) DEFAULT NULL,
  `email` varchar(50) NOT NULL,
  PRIMARY KEY (`studentid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `students`
--

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
INSERT INTO `students` VALUES (1,'911524205001','ABICHETHRA P','IT','Third year',''),(2,'911524205002','ABIRAMI K','IT','Third year',''),(3,'911524205003','AFRIN JAISHA S','IT','Third year','afrinjaisha123@gmail.com'),(4,'911524205004','AHAMED RASIK FARITH S','IT','Third year','farithrasik7@gmail.com'),(5,'911524205005','AHAMED SHAKIL Z','IT','Third year',''),(6,'911524205006','AL AFRAAH S','IT','Third year',''),(7,'911524205007','ALBUN VINOJ','IT','Third year','albanvinoj2006@gmail.com'),(8,'911524205008','APRITH LENAN R.J','IT','Third year',''),(9,'911524205009','ASLAN SHA A','IT','Third year',''),(10,'911524205010','BAHIYA SRI K','IT','Third year',''),(11,'911524205011','BALAGANESH V','IT','Third year',''),(12,'911524205012','DEVIKA P','IT','Third year',''),(13,'911524205013','EDINA SHERIN A','IT','Third year',''),(14,'911524205015','FAHIMA PARVEEN W','IT','Third year',''),(15,'911524205016','FATHIMA FARHA M','IT','Third year','shahulrayan03@gmail.com'),(16,'911524205017','HARISH KUMAR R','IT','Third year','mgsg208@gmail.com'),(17,'911524205018','HARSHINI R','IT','Third year',''),(18,'911524205019','ISMAIL D','IT','Third year','mr.gentle767@gmail.com'),(19,'911524205020','JEEVA N','IT','Third year','mjogaming65@gmail.com'),(20,'911524205021','KALINIRANJAN K','IT','Third year','kaliniranjan2007@gmail.com'),(21,'911524205022','KARAN M','IT','Third year',''),(22,'911524205023','KEERTHIGA M','IT','Third year',''),(23,'911524205024','LAKSHMI NARAYANAN R','IT','Third year',''),(24,'911524205025','LITHISH K','IT','Third year','lithishkannan6@gmail.com'),(25,'911524205026','MATHANBABU M','IT','Third year',''),(26,'911524205027','MOHAMED AATHIF H','IT','Third year',''),(27,'911524205028','MOHAMED FAREETH K','IT','Third year',''),(28,'911524205029','MOHAMED HAJA NAWAS J','IT','Third year',''),(29,'911524205030','MOHAMED NIHMATHULLAH S','IT','Third year','nihmathuu@gmail.com'),(30,'911524205031','MOHAMED SAJEER S','IT','Third year',''),(31,'911524205032','MOHAMED SHEEDHU N','IT','Third year','sheedh1980@gmail.com'),(32,'911524205033','MOHAMED THAMEEM ANSARI S','IT','Third year',''),(33,'911524205034','MUNEESWARAN S','IT','Third year',''),(34,'911524205035','NAAZIR MEERAN K','IT','Third year',''),(35,'911524205036','NANDHINI R','IT','Third year',''),(36,'911524205037','NIKILAN A','IT','Third year',''),(37,'911524205038','NOORUL THAHANI K','IT','Third year',''),(38,'911524205039','PAZHANELAVANYA S','IT','Third year',''),(39,'911524205040','PRITHIVIRAJ S','IT','Third year',''),(40,'911524205041','RAHUL SANJAI R','IT','Third year',''),(41,'911524205042','ROHITH RAJA A','IT','Third year',''),(42,'911524205043','SAFRAN AATHIKA H','IT','Third year',''),(43,'911524205044','SANJEEV PRAKASH','IT','Third year',''),(44,'911524205045','SARAFATH AHMED S','IT','Third year','sarafathahmed73@gmail.com'),(45,'911524205046','SHABIYA THABASUM M','IT','Third year',''),(46,'911524205047','SHAFAANA KHAALIDA S','IT','Third year','khaalidashafaana@gmail.com'),(47,'911524205048','SHAKILA SRI T','IT','Third year',''),(48,'911524205049','SIBI SHARVESH M','IT','Third year',''),(49,'911524205050','SIFAUL ZABEEN M','IT','Third year','sifaulzabeen6@gmail.com'),(50,'911524205051','SUMAIYA S','IT','Third year','alsumaiya744@gmail.com'),(51,'911524205052','SWARNIKA B','IT','Third year',''),(52,'911524205301','ABRISH SANJAY','IT','Third year',''),(53,'911524205302','DEVNATH C','IT','Third year',''),(54,'911524205303','KANAGAVEL J','IT','Third year',''),(55,'911524205304','MANOJKUMAR S','IT','Third year',''),(56,'911524205305','MOHAMMED ASLAM','IT','Third year','mohamedaslaam2004@gmail.com'),(57,'911524205306','MOHAMED HAAFIL H','IT','Third year',''),(58,'911524205307','MOHAMED JASIR','IT','Third year',''),(59,'911524205308','RUTHISKAVI K','IT','Third year',''),(60,'911524205309','SAMIH ANSAR','IT','Third year','samihansar8@gmail.com'),(61,'911524205310','SYED ASHAKEEN','IT','Third year','syedashakkeen@gmail.com'),(62,'911524205311','VISHWA S','IT','Third year','svishwa22062006@gmail.com');
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-30 13:00:34
