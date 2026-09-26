-- MySQL dump 10.13  Distrib 8.4.11, for Win64 (x86_64)
--
-- Host: localhost    Database: db_sdgames
-- ------------------------------------------------------
-- Server version	8.4.11

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `appprincipal_boleta`
--

DROP TABLE IF EXISTS `appprincipal_boleta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_boleta` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fecha_emision` datetime(6) NOT NULL,
  `archivo_pdf` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `venta_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `venta_id` (`venta_id`),
  CONSTRAINT `appPrincipal_boleta_venta_id_937bbb72_fk_appPrincipal_venta_id` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_boleta`
--

LOCK TABLES `appprincipal_boleta` WRITE;
/*!40000 ALTER TABLE `appprincipal_boleta` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_boleta` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_carrito`
--

DROP TABLE IF EXISTS `appprincipal_carrito`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_carrito` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `appPrincipal_carrito_usuario_id_3cbf28de_fk_appPrinci` (`usuario_id`),
  CONSTRAINT `appPrincipal_carrito_usuario_id_3cbf28de_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_carrito`
--

LOCK TABLES `appprincipal_carrito` WRITE;
/*!40000 ALTER TABLE `appprincipal_carrito` DISABLE KEYS */;
INSERT INTO `appprincipal_carrito` VALUES (1,3);
/*!40000 ALTER TABLE `appprincipal_carrito` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_devolucion`
--

DROP TABLE IF EXISTS `appprincipal_devolucion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_devolucion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fecha_solicitud` datetime(6) NOT NULL,
  `motivo` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `estado` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `respuesta_admin` longtext COLLATE utf8mb4_general_ci,
  `fecha_resolucion` datetime(6) DEFAULT NULL,
  `producto_id` bigint DEFAULT NULL,
  `usuario_id` bigint NOT NULL,
  `venta_id` bigint DEFAULT NULL,
  `cantidad` int unsigned NOT NULL,
  `imagen1` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `imagen2` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `imagen3` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `appPrincipal_devoluc_producto_id_85856ca4_fk_appPrinci` (`producto_id`),
  KEY `appPrincipal_devoluc_usuario_id_4ca389c6_fk_appPrinci` (`usuario_id`),
  KEY `appPrincipal_devoluc_venta_id_2a9b1c77_fk_appPrinci` (`venta_id`),
  CONSTRAINT `appPrincipal_devoluc_producto_id_85856ca4_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  CONSTRAINT `appPrincipal_devoluc_usuario_id_4ca389c6_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`),
  CONSTRAINT `appPrincipal_devoluc_venta_id_2a9b1c77_fk_appPrinci` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`),
  CONSTRAINT `appprincipal_devolucion_chk_1` CHECK ((`cantidad` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_devolucion`
--

LOCK TABLES `appprincipal_devolucion` WRITE;
/*!40000 ALTER TABLE `appprincipal_devolucion` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_devolucion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_envio`
--

DROP TABLE IF EXISTS `appprincipal_envio`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_envio` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `numero_seguimiento` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fecha_envio` datetime(6) DEFAULT NULL,
  `fecha_entrega` datetime(6) DEFAULT NULL,
  `estado` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `transportista` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `venta_id` bigint NOT NULL,
  `fecha_preparacion` datetime(6) DEFAULT NULL,
  `fecha_reparto` datetime(6) DEFAULT NULL,
  `fecha_transito` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `venta_id` (`venta_id`),
  CONSTRAINT `appPrincipal_envio_venta_id_ce3fcdfe_fk_appPrincipal_venta_id` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_envio`
--

LOCK TABLES `appprincipal_envio` WRITE;
/*!40000 ALTER TABLE `appprincipal_envio` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_envio` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_favorito`
--

DROP TABLE IF EXISTS `appprincipal_favorito`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_favorito` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `producto_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `appPrincipal_favorit_producto_id_e0cd3670_fk_appPrinci` (`producto_id`),
  KEY `appPrincipal_favorit_usuario_id_ec4c3124_fk_appPrinci` (`usuario_id`),
  CONSTRAINT `appPrincipal_favorit_producto_id_e0cd3670_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  CONSTRAINT `appPrincipal_favorit_usuario_id_ec4c3124_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_favorito`
--

LOCK TABLES `appprincipal_favorito` WRITE;
/*!40000 ALTER TABLE `appprincipal_favorito` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_favorito` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_itemcarritoproducto`
--

DROP TABLE IF EXISTS `appprincipal_itemcarritoproducto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_itemcarritoproducto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `cantidad` int unsigned NOT NULL,
  `carrito_id` bigint NOT NULL,
  `producto_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `appPrincipal_itemcar_carrito_id_fd140a06_fk_appPrinci` (`carrito_id`),
  KEY `appPrincipal_itemcar_producto_id_f6f9a776_fk_appPrinci` (`producto_id`),
  CONSTRAINT `appPrincipal_itemcar_carrito_id_fd140a06_fk_appPrinci` FOREIGN KEY (`carrito_id`) REFERENCES `appprincipal_carrito` (`id`),
  CONSTRAINT `appPrincipal_itemcar_producto_id_f6f9a776_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  CONSTRAINT `appprincipal_itemcarritoproducto_chk_1` CHECK ((`cantidad` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_itemcarritoproducto`
--

LOCK TABLES `appprincipal_itemcarritoproducto` WRITE;
/*!40000 ALTER TABLE `appprincipal_itemcarritoproducto` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_itemcarritoproducto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_opinion`
--

DROP TABLE IF EXISTS `appprincipal_opinion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_opinion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `comentario` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `puntuacion` int unsigned NOT NULL,
  `fecha_creacion` datetime(6) NOT NULL,
  `producto_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `appPrincipal_opinion_usuario_id_producto_id_f9904218_uniq` (`usuario_id`,`producto_id`),
  KEY `appPrincipal_opinion_producto_id_7cd6214d_fk_appPrinci` (`producto_id`),
  CONSTRAINT `appPrincipal_opinion_producto_id_7cd6214d_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  CONSTRAINT `appPrincipal_opinion_usuario_id_a6b8154e_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`),
  CONSTRAINT `appprincipal_opinion_chk_1` CHECK ((`puntuacion` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_opinion`
--

LOCK TABLES `appprincipal_opinion` WRITE;
/*!40000 ALTER TABLE `appprincipal_opinion` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_opinion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_producto`
--

DROP TABLE IF EXISTS `appprincipal_producto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_producto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `codigo_de_barra` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `precio` int unsigned NOT NULL,
  `stock` int unsigned NOT NULL,
  `descripcion` longtext COLLATE utf8mb4_general_ci,
  `imagen_principal` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `imagen_2` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `imagen_3` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `imagen_4` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `imagen_5` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `imagen_6` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `categoria` varchar(40) COLLATE utf8mb4_general_ci NOT NULL,
  `genero` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `deleted_at` datetime(6) DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `appprincipal_producto_chk_1` CHECK ((`precio` >= 0)),
  CONSTRAINT `appprincipal_producto_chk_2` CHECK ((`stock` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_producto`
--

LOCK TABLES `appprincipal_producto` WRITE;
/*!40000 ALTER TABLE `appprincipal_producto` DISABLE KEYS */;
INSERT INTO `appprincipal_producto` VALUES (1,'23423423','Silent Hill 2',33990,20,'Silent Hill 2 es un videojuego de terror psicológico y supervivencia desarrollado por Team Silent, un grupo de Konami Computer Entertainment Tokyo, y publicado por Konami para PlayStation 2.','productos/silent.png','','','','','','Videojuegos PS5','TERROR',NULL,0),(2,'432423423','Fc 25',27990,10,'EA Sports FC 25 es un videojuego de fútbol, desarrollado por EA, y publicado por EA Sports. Es la segunda entrega de la serie EA Sports FC y la trigésimo segunda si se incluyen las entregas bajo el nombre de EA Sports FIFA, conocido popularmente como FIFA.','productos/fc25.png','','','','','','Videojuegos XBOX SERIES','DEPORTES',NULL,0),(3,'3242432342','Call of Duty: Black Ops 6',40990,13,'Call of Duty: Black Ops 6 es un videojuego de acción de disparos en primera persona desarrollado por Treyarch y Raven Software y publicado por Activision. Es la vigésima primera entrega de la serie Call of Duty y es la sexta entrada principal de la subserie Black Ops, después de Call of Duty: Black Ops Cold War.','productos/cod6.png','','','','','','Videojuegos PS5','ACCION',NULL,0),(4,'3242334243','Control Sony Dualsense Chroma Pearl Ps5',50990,20,'Con Sony no solo podrás ver y escuchar todo con más detalle, sino que también sentirás vibraciones mucho más intensas.\r\nToma el control con mayor comodidad, disfruta de un sonido de alta fidelidad y gana precisión en el juego gracias a las mejoras en su diseño y botones.\r\n\r\nMayor comodidad y realismo\r\nPermite jugar sin necesidad de cables en el medio. Está diseñado no solo para controlar mejor tus videojuegos, sino también para aumentar tu realismo y experiencia.\r\n\r\nActiva el Bluetooth\r\nCuenta con una conexión Bluetooth de alta tecnología para usarla en cualquier ordenador o dispositivo; ya no necesitarás aplicaciones de terceros ni un cable USB. Además, tiene una gran capacidad antiinterferente, un fácil manejo y una señal de conexión estable.','productos/chroma.png','','','','','','Accesorios PS5','ACCESORIOS',NULL,0),(5,'35532452335','Play Station 5',520990,20,'Disfruta de tiempos de carga superveloces con un SSD de velocidad ultrarrápida, una experiencia más inmersiva gracias a la compatibilidad con respuesta háptica1, gatillos adaptativos1 y audio 3D1, además de una increíble colección de juegos de PlayStation.','productos/ps5_consola_fisico_021-52fb99d678ac79046b16484924210844-1024-1024.jpg','productos/sony-consolas-playstation-5-ps5.jpg','productos/50564842523_8146f80c8d_k_FjLJpnd.jpg','productos/50544735806_dd39e95f06_h.jpg','productos/50544012768_bdcd8add7c_h.jpg','','Ps5 Consolas','CONSOLAS',NULL,0),(6,'32523525235','Funko Pop John Wick',10990,4,'DESCRIPCIÓN\r\n\r\nAviso legal\r\n• La edad mínima recomendada para utilizarla es 3 años.','productos/jon1.png','productos/jon2.png','','','','','Figuras Funko','FIGURAS',NULL,0);
/*!40000 ALTER TABLE `appprincipal_producto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_productoventa`
--

DROP TABLE IF EXISTS `appprincipal_productoventa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_productoventa` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `cantidad` int unsigned NOT NULL,
  `precio_unitario` int unsigned NOT NULL,
  `producto_id` bigint NOT NULL,
  `venta_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `appPrincipal_product_producto_id_29685283_fk_appPrinci` (`producto_id`),
  KEY `appPrincipal_product_venta_id_d5ea0264_fk_appPrinci` (`venta_id`),
  CONSTRAINT `appPrincipal_product_producto_id_29685283_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  CONSTRAINT `appPrincipal_product_venta_id_d5ea0264_fk_appPrinci` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`),
  CONSTRAINT `appprincipal_productoventa_chk_1` CHECK ((`cantidad` >= 0)),
  CONSTRAINT `appprincipal_productoventa_chk_2` CHECK ((`precio_unitario` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_productoventa`
--

LOCK TABLES `appprincipal_productoventa` WRITE;
/*!40000 ALTER TABLE `appprincipal_productoventa` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_productoventa` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_reclamo`
--

DROP TABLE IF EXISTS `appprincipal_reclamo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_reclamo` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `estado` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `asunto` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `fecha` datetime(6) NOT NULL,
  `descripcion` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `respuesta` longtext COLLATE utf8mb4_general_ci,
  `usuario_id` bigint NOT NULL,
  `venta_id` bigint DEFAULT NULL,
  `fecha_respuesta` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `appPrincipal_reclamo_usuario_id_7e40b1ff_fk_appPrinci` (`usuario_id`),
  KEY `appPrincipal_reclamo_venta_id_311556f5_fk_appPrincipal_venta_id` (`venta_id`),
  CONSTRAINT `appPrincipal_reclamo_usuario_id_7e40b1ff_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`),
  CONSTRAINT `appPrincipal_reclamo_venta_id_311556f5_fk_appPrincipal_venta_id` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_reclamo`
--

LOCK TABLES `appprincipal_reclamo` WRITE;
/*!40000 ALTER TABLE `appprincipal_reclamo` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_reclamo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_usuario`
--

DROP TABLE IF EXISTS `appprincipal_usuario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_usuario` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_general_ci NOT NULL,
  `contraseña` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `rut` varchar(12) COLLATE utf8mb4_general_ci NOT NULL,
  `telefono` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `direccion` varchar(120) COLLATE utf8mb4_general_ci NOT NULL,
  `region` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `ciudad` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `es_administrador` tinyint(1) NOT NULL,
  `deleted_at` datetime(6) DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `rut` (`rut`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_usuario`
--

LOCK TABLES `appprincipal_usuario` WRITE;
/*!40000 ALTER TABLE `appprincipal_usuario` DISABLE KEYS */;
INSERT INTO `appprincipal_usuario` VALUES (2,'Admin','admin@gmail.com','pbkdf2_sha256$600000$5GoOxDn7kWLnaoi8OlvZ0e$BTr6s/Q8+ktfOzy0O56xaEHkp9xOUKLaxn9Rr3T4uE0=','12.343.455-2','+56 9 45533453','Picarte 233','LOS RIOS','Valdivia',1,NULL,0),(3,'Usuario','user@gmail.com','pbkdf2_sha256$600000$sc2VSSUnmVeKMkEKll3APi$vQjkc6MSYmOYwm6hWRE6XfoLadNSNgl8nLsa32qyqW8=','75.292.177-6','+56 9 45645354','Gabriela Mistral 345','VALPARAISO','Viña del Mar',0,NULL,0);
/*!40000 ALTER TABLE `appprincipal_usuario` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appprincipal_venta`
--

DROP TABLE IF EXISTS `appprincipal_venta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appprincipal_venta` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `envio` int unsigned NOT NULL,
  `subtotal` int unsigned NOT NULL,
  `total` int unsigned NOT NULL,
  `estado` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `fecha` datetime(6) NOT NULL,
  `metodo_envio` varchar(10) COLLATE utf8mb4_general_ci NOT NULL,
  `direccion_envio` longtext COLLATE utf8mb4_general_ci,
  `carrito_id` bigint DEFAULT NULL,
  `usuario_id` bigint NOT NULL,
  `metodo_pago` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `appPrincipal_venta_carrito_id_d11473a4_fk_appPrinci` (`carrito_id`),
  KEY `appPrincipal_venta_usuario_id_a424aa2e_fk_appPrinci` (`usuario_id`),
  CONSTRAINT `appPrincipal_venta_carrito_id_d11473a4_fk_appPrinci` FOREIGN KEY (`carrito_id`) REFERENCES `appprincipal_carrito` (`id`),
  CONSTRAINT `appPrincipal_venta_usuario_id_a424aa2e_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`),
  CONSTRAINT `appprincipal_venta_chk_1` CHECK ((`envio` >= 0)),
  CONSTRAINT `appprincipal_venta_chk_2` CHECK ((`subtotal` >= 0)),
  CONSTRAINT `appprincipal_venta_chk_3` CHECK ((`total` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `appprincipal_venta`
--

LOCK TABLES `appprincipal_venta` WRITE;
/*!40000 ALTER TABLE `appprincipal_venta` DISABLE KEYS */;
/*!40000 ALTER TABLE `appprincipal_venta` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add session',6,'add_session'),(22,'Can change session',6,'change_session'),(23,'Can delete session',6,'delete_session'),(24,'Can view session',6,'view_session'),(25,'Can add carrito',7,'add_carrito'),(26,'Can change carrito',7,'change_carrito'),(27,'Can delete carrito',7,'delete_carrito'),(28,'Can view carrito',7,'view_carrito'),(29,'Can add producto',8,'add_producto'),(30,'Can change producto',8,'change_producto'),(31,'Can delete producto',8,'delete_producto'),(32,'Can view producto',8,'view_producto'),(33,'Can add usuario',9,'add_usuario'),(34,'Can change usuario',9,'change_usuario'),(35,'Can delete usuario',9,'delete_usuario'),(36,'Can view usuario',9,'view_usuario'),(37,'Can add item carrito producto',10,'add_itemcarritoproducto'),(38,'Can change item carrito producto',10,'change_itemcarritoproducto'),(39,'Can delete item carrito producto',10,'delete_itemcarritoproducto'),(40,'Can view item carrito producto',10,'view_itemcarritoproducto'),(41,'Can add reclamo',11,'add_reclamo'),(42,'Can change reclamo',11,'change_reclamo'),(43,'Can delete reclamo',11,'delete_reclamo'),(44,'Can view reclamo',11,'view_reclamo'),(45,'Can add favorito',12,'add_favorito'),(46,'Can change favorito',12,'change_favorito'),(47,'Can delete favorito',12,'delete_favorito'),(48,'Can view favorito',12,'view_favorito'),(49,'Can add venta',13,'add_venta'),(50,'Can change venta',13,'change_venta'),(51,'Can delete venta',13,'delete_venta'),(52,'Can view venta',13,'view_venta'),(53,'Can add producto venta',14,'add_productoventa'),(54,'Can change producto venta',14,'change_productoventa'),(55,'Can delete producto venta',14,'delete_productoventa'),(56,'Can view producto venta',14,'view_productoventa'),(57,'Can add Opinión',15,'add_opinion'),(58,'Can change Opinión',15,'change_opinion'),(59,'Can delete Opinión',15,'delete_opinion'),(60,'Can view Opinión',15,'view_opinion'),(61,'Can add envio',16,'add_envio'),(62,'Can change envio',16,'change_envio'),(63,'Can delete envio',16,'delete_envio'),(64,'Can view envio',16,'view_envio'),(65,'Can add devolucion',17,'add_devolucion'),(66,'Can change devolucion',17,'change_devolucion'),(67,'Can delete devolucion',17,'delete_devolucion'),(68,'Can view devolucion',17,'view_devolucion'),(69,'Can add boleta',18,'add_boleta'),(70,'Can change boleta',18,'change_boleta'),(71,'Can delete boleta',18,'delete_boleta'),(72,'Can view boleta',18,'view_boleta');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_general_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_general_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_general_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_general_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(18,'appPrincipal','boleta'),(7,'appPrincipal','carrito'),(17,'appPrincipal','devolucion'),(16,'appPrincipal','envio'),(12,'appPrincipal','favorito'),(10,'appPrincipal','itemcarritoproducto'),(15,'appPrincipal','opinion'),(8,'appPrincipal','producto'),(14,'appPrincipal','productoventa'),(11,'appPrincipal','reclamo'),(9,'appPrincipal','usuario'),(13,'appPrincipal','venta'),(3,'auth','group'),(2,'auth','permission'),(4,'auth','user'),(5,'contenttypes','contenttype'),(6,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-04-04 00:08:08.358861'),(2,'auth','0001_initial','2026-04-04 00:08:08.461451'),(3,'admin','0001_initial','2026-04-04 00:08:08.485488'),(4,'admin','0002_logentry_remove_auto_add','2026-04-04 00:08:08.490788'),(5,'admin','0003_logentry_add_action_flag_choices','2026-04-04 00:08:08.495792'),(6,'appPrincipal','0001_initial','2026-04-04 00:08:08.654109'),(7,'appPrincipal','0002_usuario_es_administrador','2026-04-04 00:08:08.665248'),(8,'appPrincipal','0003_envio_devolucion_boleta','2026-04-04 00:08:08.739810'),(9,'appPrincipal','0004_venta_metodo_pago','2026-04-04 00:08:08.750012'),(10,'appPrincipal','0005_producto_deleted_at_producto_is_deleted_and_more','2026-04-04 00:08:08.793926'),(11,'appPrincipal','0006_rename_fecha_entrega_envio_fecha_entregado_and_more','2026-04-04 00:08:08.829675'),(12,'appPrincipal','0007_rename_fecha_entregado_envio_fecha_entrega','2026-04-04 00:08:08.838724'),(13,'appPrincipal','0008_alter_producto_codigo_de_barra','2026-04-04 00:08:09.777101'),(14,'appPrincipal','0009_alter_envio_estado','2026-04-04 00:08:09.782454'),(15,'appPrincipal','0010_reclamo_venta','2026-04-04 00:08:09.797900'),(16,'appPrincipal','0011_devolucion_cantidad','2026-04-04 00:08:09.811053'),(17,'appPrincipal','0012_devolucion_imagen1_devolucion_imagen2_and_more','2026-04-04 00:08:09.848128'),(18,'appPrincipal','0013_reclamo_fecha_respuesta','2026-04-04 00:08:09.858041'),(19,'contenttypes','0002_remove_content_type_name','2026-04-04 00:08:09.881552'),(20,'auth','0002_alter_permission_name_max_length','2026-04-04 00:08:09.895896'),(21,'auth','0003_alter_user_email_max_length','2026-04-04 00:08:09.906370'),(22,'auth','0004_alter_user_username_opts','2026-04-04 00:08:09.911877'),(23,'auth','0005_alter_user_last_login_null','2026-04-04 00:08:09.923881'),(24,'auth','0006_require_contenttypes_0002','2026-04-04 00:08:09.926214'),(25,'auth','0007_alter_validators_add_error_messages','2026-04-04 00:08:09.931373'),(26,'auth','0008_alter_user_username_max_length','2026-04-04 00:08:09.941280'),(27,'auth','0009_alter_user_last_name_max_length','2026-04-04 00:08:09.950780'),(28,'auth','0010_alter_group_name_max_length','2026-04-04 00:08:09.959785'),(29,'auth','0011_update_proxy_permissions','2026-04-04 00:08:09.968707'),(30,'auth','0012_alter_user_first_name_max_length','2026-04-04 00:08:09.978579'),(31,'sessions','0001_initial','2026-04-04 00:08:09.989579');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_general_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('lvhpau7h3cqb1ls2hgc1hwaqfuc3quxa','eyJ1c3VhcmlvX2lkIjozfQ:1xAGPz:jNx0LV7QlsysVxshDQu05Sc3qbTguoCguhRjfHehQZQ','2026-09-26 01:37:31.031806');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-25 21:44:38
