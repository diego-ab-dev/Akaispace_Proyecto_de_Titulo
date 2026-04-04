-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 04-04-2026 a las 03:35:40
-- Versión del servidor: 11.5.2-MariaDB
-- Versión de PHP: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `db_sdgames`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_boleta`
--

CREATE TABLE `appprincipal_boleta` (
  `id` bigint(20) NOT NULL,
  `fecha_emision` datetime(6) NOT NULL,
  `archivo_pdf` varchar(100) DEFAULT NULL,
  `venta_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_carrito`
--

CREATE TABLE `appprincipal_carrito` (
  `id` bigint(20) NOT NULL,
  `usuario_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `appprincipal_carrito`
--

INSERT INTO `appprincipal_carrito` (`id`, `usuario_id`) VALUES
(1, 3);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_devolucion`
--

CREATE TABLE `appprincipal_devolucion` (
  `id` bigint(20) NOT NULL,
  `fecha_solicitud` datetime(6) NOT NULL,
  `motivo` longtext NOT NULL,
  `estado` varchar(20) NOT NULL,
  `respuesta_admin` longtext DEFAULT NULL,
  `fecha_resolucion` datetime(6) DEFAULT NULL,
  `producto_id` bigint(20) DEFAULT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `venta_id` bigint(20) DEFAULT NULL,
  `cantidad` int(10) UNSIGNED NOT NULL CHECK (`cantidad` >= 0),
  `imagen1` varchar(100) DEFAULT NULL,
  `imagen2` varchar(100) DEFAULT NULL,
  `imagen3` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_envio`
--

CREATE TABLE `appprincipal_envio` (
  `id` bigint(20) NOT NULL,
  `numero_seguimiento` varchar(50) DEFAULT NULL,
  `fecha_envio` datetime(6) DEFAULT NULL,
  `fecha_entrega` datetime(6) DEFAULT NULL,
  `estado` varchar(20) NOT NULL,
  `transportista` varchar(50) NOT NULL,
  `venta_id` bigint(20) NOT NULL,
  `fecha_preparacion` datetime(6) DEFAULT NULL,
  `fecha_reparto` datetime(6) DEFAULT NULL,
  `fecha_transito` datetime(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_favorito`
--

CREATE TABLE `appprincipal_favorito` (
  `id` bigint(20) NOT NULL,
  `producto_id` bigint(20) NOT NULL,
  `usuario_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_itemcarritoproducto`
--

CREATE TABLE `appprincipal_itemcarritoproducto` (
  `id` bigint(20) NOT NULL,
  `cantidad` int(10) UNSIGNED NOT NULL CHECK (`cantidad` >= 0),
  `carrito_id` bigint(20) NOT NULL,
  `producto_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_opinion`
--

CREATE TABLE `appprincipal_opinion` (
  `id` bigint(20) NOT NULL,
  `comentario` longtext NOT NULL,
  `puntuacion` int(10) UNSIGNED NOT NULL CHECK (`puntuacion` >= 0),
  `fecha_creacion` datetime(6) NOT NULL,
  `producto_id` bigint(20) NOT NULL,
  `usuario_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_producto`
--

CREATE TABLE `appprincipal_producto` (
  `id` bigint(20) NOT NULL,
  `codigo_de_barra` varchar(20) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `precio` int(10) UNSIGNED NOT NULL CHECK (`precio` >= 0),
  `stock` int(10) UNSIGNED NOT NULL CHECK (`stock` >= 0),
  `descripcion` longtext DEFAULT NULL,
  `imagen_principal` varchar(100) NOT NULL,
  `imagen_2` varchar(100) DEFAULT NULL,
  `imagen_3` varchar(100) DEFAULT NULL,
  `imagen_4` varchar(100) DEFAULT NULL,
  `imagen_5` varchar(100) DEFAULT NULL,
  `imagen_6` varchar(100) DEFAULT NULL,
  `categoria` varchar(40) NOT NULL,
  `genero` varchar(20) NOT NULL,
  `deleted_at` datetime(6) DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `appprincipal_producto`
--

INSERT INTO `appprincipal_producto` (`id`, `codigo_de_barra`, `nombre`, `precio`, `stock`, `descripcion`, `imagen_principal`, `imagen_2`, `imagen_3`, `imagen_4`, `imagen_5`, `imagen_6`, `categoria`, `genero`, `deleted_at`, `is_deleted`) VALUES
(1, '23423423', 'Silent Hill 2', 33990, 20, 'Silent Hill 2 es un videojuego de terror psicológico y supervivencia desarrollado por Team Silent, un grupo de Konami Computer Entertainment Tokyo, y publicado por Konami para PlayStation 2.', 'productos/silent.png', '', '', '', '', '', 'Videojuegos PS5', 'TERROR', NULL, 0),
(2, '432423423', 'Fc 25', 27990, 10, 'EA Sports FC 25 es un videojuego de fútbol, desarrollado por EA, y publicado por EA Sports. Es la segunda entrega de la serie EA Sports FC y la trigésimo segunda si se incluyen las entregas bajo el nombre de EA Sports FIFA, conocido popularmente como FIFA.', 'productos/fc25.png', '', '', '', '', '', 'Videojuegos XBOX SERIES', 'DEPORTES', NULL, 0),
(3, '3242432342', 'Call of Duty: Black Ops 6', 40990, 13, 'Call of Duty: Black Ops 6 es un videojuego de acción de disparos en primera persona desarrollado por Treyarch y Raven Software y publicado por Activision. Es la vigésima primera entrega de la serie Call of Duty y es la sexta entrada principal de la subserie Black Ops, después de Call of Duty: Black Ops Cold War.', 'productos/cod6.png', '', '', '', '', '', 'Videojuegos PS5', 'ACCION', NULL, 0),
(4, '3242334243', 'Control Sony Dualsense Chroma Pearl Ps5', 50990, 20, 'Con Sony no solo podrás ver y escuchar todo con más detalle, sino que también sentirás vibraciones mucho más intensas.\r\nToma el control con mayor comodidad, disfruta de un sonido de alta fidelidad y gana precisión en el juego gracias a las mejoras en su diseño y botones.\r\n\r\nMayor comodidad y realismo\r\nPermite jugar sin necesidad de cables en el medio. Está diseñado no solo para controlar mejor tus videojuegos, sino también para aumentar tu realismo y experiencia.\r\n\r\nActiva el Bluetooth\r\nCuenta con una conexión Bluetooth de alta tecnología para usarla en cualquier ordenador o dispositivo; ya no necesitarás aplicaciones de terceros ni un cable USB. Además, tiene una gran capacidad antiinterferente, un fácil manejo y una señal de conexión estable.', 'productos/chroma.png', '', '', '', '', '', 'Accesorios PS5', 'ACCESORIOS', NULL, 0),
(5, '35532452335', 'Play Station 5', 520990, 20, 'Disfruta de tiempos de carga superveloces con un SSD de velocidad ultrarrápida, una experiencia más inmersiva gracias a la compatibilidad con respuesta háptica1, gatillos adaptativos1 y audio 3D1, además de una increíble colección de juegos de PlayStation.', 'productos/ps5_consola_fisico_021-52fb99d678ac79046b16484924210844-1024-1024.jpg', 'productos/sony-consolas-playstation-5-ps5.jpg', 'productos/50564842523_8146f80c8d_k_FjLJpnd.jpg', 'productos/50544735806_dd39e95f06_h.jpg', 'productos/50544012768_bdcd8add7c_h.jpg', '', 'Ps5 Consolas', 'CONSOLAS', NULL, 0),
(6, '32523525235', 'Funko Pop John Wick', 10990, 4, 'DESCRIPCIÓN\r\n\r\nAviso legal\r\n• La edad mínima recomendada para utilizarla es 3 años.', 'productos/jon1.png', 'productos/jon2.png', '', '', '', '', 'Figuras Funko', 'FIGURAS', NULL, 0);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_productoventa`
--

CREATE TABLE `appprincipal_productoventa` (
  `id` bigint(20) NOT NULL,
  `cantidad` int(10) UNSIGNED NOT NULL CHECK (`cantidad` >= 0),
  `precio_unitario` int(10) UNSIGNED NOT NULL CHECK (`precio_unitario` >= 0),
  `producto_id` bigint(20) NOT NULL,
  `venta_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_reclamo`
--

CREATE TABLE `appprincipal_reclamo` (
  `id` bigint(20) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `asunto` varchar(255) NOT NULL,
  `fecha` datetime(6) NOT NULL,
  `descripcion` longtext NOT NULL,
  `respuesta` longtext DEFAULT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `venta_id` bigint(20) DEFAULT NULL,
  `fecha_respuesta` datetime(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_usuario`
--

CREATE TABLE `appprincipal_usuario` (
  `id` bigint(20) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(254) NOT NULL,
  `contraseña` varchar(100) NOT NULL,
  `rut` varchar(12) NOT NULL,
  `telefono` varchar(20) NOT NULL,
  `direccion` varchar(120) NOT NULL,
  `region` varchar(100) NOT NULL,
  `ciudad` varchar(100) NOT NULL,
  `es_administrador` tinyint(1) NOT NULL,
  `deleted_at` datetime(6) DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `appprincipal_usuario`
--

INSERT INTO `appprincipal_usuario` (`id`, `nombre`, `email`, `contraseña`, `rut`, `telefono`, `direccion`, `region`, `ciudad`, `es_administrador`, `deleted_at`, `is_deleted`) VALUES
(2, 'Admin', 'admin@gmail.com', 'pbkdf2_sha256$600000$5GoOxDn7kWLnaoi8OlvZ0e$BTr6s/Q8+ktfOzy0O56xaEHkp9xOUKLaxn9Rr3T4uE0=', '12.343.455-2', '+56 9 45533453', 'Picarte 233', 'LOS RIOS', 'Valdivia', 1, NULL, 0),
(3, 'Usuario', 'user@gmail.com', 'pbkdf2_sha256$600000$sc2VSSUnmVeKMkEKll3APi$vQjkc6MSYmOYwm6hWRE6XfoLadNSNgl8nLsa32qyqW8=', '75.292.177-6', '+56 9 45645354', 'Gabriela Mistral 345', 'VALPARAISO', 'Viña del Mar', 0, NULL, 0);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `appprincipal_venta`
--

CREATE TABLE `appprincipal_venta` (
  `id` bigint(20) NOT NULL,
  `envio` int(10) UNSIGNED NOT NULL CHECK (`envio` >= 0),
  `subtotal` int(10) UNSIGNED NOT NULL CHECK (`subtotal` >= 0),
  `total` int(10) UNSIGNED NOT NULL CHECK (`total` >= 0),
  `estado` varchar(20) NOT NULL,
  `fecha` datetime(6) NOT NULL,
  `metodo_envio` varchar(10) NOT NULL,
  `direccion_envio` longtext DEFAULT NULL,
  `carrito_id` bigint(20) DEFAULT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `metodo_pago` varchar(30) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_group`
--

CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL,
  `name` varchar(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_group_permissions`
--

CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_permission`
--

CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `auth_permission`
--

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
(1, 'Can add log entry', 1, 'add_logentry'),
(2, 'Can change log entry', 1, 'change_logentry'),
(3, 'Can delete log entry', 1, 'delete_logentry'),
(4, 'Can view log entry', 1, 'view_logentry'),
(5, 'Can add permission', 2, 'add_permission'),
(6, 'Can change permission', 2, 'change_permission'),
(7, 'Can delete permission', 2, 'delete_permission'),
(8, 'Can view permission', 2, 'view_permission'),
(9, 'Can add group', 3, 'add_group'),
(10, 'Can change group', 3, 'change_group'),
(11, 'Can delete group', 3, 'delete_group'),
(12, 'Can view group', 3, 'view_group'),
(13, 'Can add user', 4, 'add_user'),
(14, 'Can change user', 4, 'change_user'),
(15, 'Can delete user', 4, 'delete_user'),
(16, 'Can view user', 4, 'view_user'),
(17, 'Can add content type', 5, 'add_contenttype'),
(18, 'Can change content type', 5, 'change_contenttype'),
(19, 'Can delete content type', 5, 'delete_contenttype'),
(20, 'Can view content type', 5, 'view_contenttype'),
(21, 'Can add session', 6, 'add_session'),
(22, 'Can change session', 6, 'change_session'),
(23, 'Can delete session', 6, 'delete_session'),
(24, 'Can view session', 6, 'view_session'),
(25, 'Can add carrito', 7, 'add_carrito'),
(26, 'Can change carrito', 7, 'change_carrito'),
(27, 'Can delete carrito', 7, 'delete_carrito'),
(28, 'Can view carrito', 7, 'view_carrito'),
(29, 'Can add producto', 8, 'add_producto'),
(30, 'Can change producto', 8, 'change_producto'),
(31, 'Can delete producto', 8, 'delete_producto'),
(32, 'Can view producto', 8, 'view_producto'),
(33, 'Can add usuario', 9, 'add_usuario'),
(34, 'Can change usuario', 9, 'change_usuario'),
(35, 'Can delete usuario', 9, 'delete_usuario'),
(36, 'Can view usuario', 9, 'view_usuario'),
(37, 'Can add item carrito producto', 10, 'add_itemcarritoproducto'),
(38, 'Can change item carrito producto', 10, 'change_itemcarritoproducto'),
(39, 'Can delete item carrito producto', 10, 'delete_itemcarritoproducto'),
(40, 'Can view item carrito producto', 10, 'view_itemcarritoproducto'),
(41, 'Can add reclamo', 11, 'add_reclamo'),
(42, 'Can change reclamo', 11, 'change_reclamo'),
(43, 'Can delete reclamo', 11, 'delete_reclamo'),
(44, 'Can view reclamo', 11, 'view_reclamo'),
(45, 'Can add favorito', 12, 'add_favorito'),
(46, 'Can change favorito', 12, 'change_favorito'),
(47, 'Can delete favorito', 12, 'delete_favorito'),
(48, 'Can view favorito', 12, 'view_favorito'),
(49, 'Can add venta', 13, 'add_venta'),
(50, 'Can change venta', 13, 'change_venta'),
(51, 'Can delete venta', 13, 'delete_venta'),
(52, 'Can view venta', 13, 'view_venta'),
(53, 'Can add producto venta', 14, 'add_productoventa'),
(54, 'Can change producto venta', 14, 'change_productoventa'),
(55, 'Can delete producto venta', 14, 'delete_productoventa'),
(56, 'Can view producto venta', 14, 'view_productoventa'),
(57, 'Can add Opinión', 15, 'add_opinion'),
(58, 'Can change Opinión', 15, 'change_opinion'),
(59, 'Can delete Opinión', 15, 'delete_opinion'),
(60, 'Can view Opinión', 15, 'view_opinion'),
(61, 'Can add envio', 16, 'add_envio'),
(62, 'Can change envio', 16, 'change_envio'),
(63, 'Can delete envio', 16, 'delete_envio'),
(64, 'Can view envio', 16, 'view_envio'),
(65, 'Can add devolucion', 17, 'add_devolucion'),
(66, 'Can change devolucion', 17, 'change_devolucion'),
(67, 'Can delete devolucion', 17, 'delete_devolucion'),
(68, 'Can view devolucion', 17, 'view_devolucion'),
(69, 'Can add boleta', 18, 'add_boleta'),
(70, 'Can change boleta', 18, 'change_boleta'),
(71, 'Can delete boleta', 18, 'delete_boleta'),
(72, 'Can view boleta', 18, 'view_boleta');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_user`
--

CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_user_groups`
--

CREATE TABLE `auth_user_groups` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_user_user_permissions`
--

CREATE TABLE `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_admin_log`
--

CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) UNSIGNED NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_content_type`
--

CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `django_content_type`
--

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(18, 'appPrincipal', 'boleta'),
(7, 'appPrincipal', 'carrito'),
(17, 'appPrincipal', 'devolucion'),
(16, 'appPrincipal', 'envio'),
(12, 'appPrincipal', 'favorito'),
(10, 'appPrincipal', 'itemcarritoproducto'),
(15, 'appPrincipal', 'opinion'),
(8, 'appPrincipal', 'producto'),
(14, 'appPrincipal', 'productoventa'),
(11, 'appPrincipal', 'reclamo'),
(9, 'appPrincipal', 'usuario'),
(13, 'appPrincipal', 'venta'),
(3, 'auth', 'group'),
(2, 'auth', 'permission'),
(4, 'auth', 'user'),
(5, 'contenttypes', 'contenttype'),
(6, 'sessions', 'session');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_migrations`
--

CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `django_migrations`
--

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2026-04-04 00:08:08.358861'),
(2, 'auth', '0001_initial', '2026-04-04 00:08:08.461451'),
(3, 'admin', '0001_initial', '2026-04-04 00:08:08.485488'),
(4, 'admin', '0002_logentry_remove_auto_add', '2026-04-04 00:08:08.490788'),
(5, 'admin', '0003_logentry_add_action_flag_choices', '2026-04-04 00:08:08.495792'),
(6, 'appPrincipal', '0001_initial', '2026-04-04 00:08:08.654109'),
(7, 'appPrincipal', '0002_usuario_es_administrador', '2026-04-04 00:08:08.665248'),
(8, 'appPrincipal', '0003_envio_devolucion_boleta', '2026-04-04 00:08:08.739810'),
(9, 'appPrincipal', '0004_venta_metodo_pago', '2026-04-04 00:08:08.750012'),
(10, 'appPrincipal', '0005_producto_deleted_at_producto_is_deleted_and_more', '2026-04-04 00:08:08.793926'),
(11, 'appPrincipal', '0006_rename_fecha_entrega_envio_fecha_entregado_and_more', '2026-04-04 00:08:08.829675'),
(12, 'appPrincipal', '0007_rename_fecha_entregado_envio_fecha_entrega', '2026-04-04 00:08:08.838724'),
(13, 'appPrincipal', '0008_alter_producto_codigo_de_barra', '2026-04-04 00:08:09.777101'),
(14, 'appPrincipal', '0009_alter_envio_estado', '2026-04-04 00:08:09.782454'),
(15, 'appPrincipal', '0010_reclamo_venta', '2026-04-04 00:08:09.797900'),
(16, 'appPrincipal', '0011_devolucion_cantidad', '2026-04-04 00:08:09.811053'),
(17, 'appPrincipal', '0012_devolucion_imagen1_devolucion_imagen2_and_more', '2026-04-04 00:08:09.848128'),
(18, 'appPrincipal', '0013_reclamo_fecha_respuesta', '2026-04-04 00:08:09.858041'),
(19, 'contenttypes', '0002_remove_content_type_name', '2026-04-04 00:08:09.881552'),
(20, 'auth', '0002_alter_permission_name_max_length', '2026-04-04 00:08:09.895896'),
(21, 'auth', '0003_alter_user_email_max_length', '2026-04-04 00:08:09.906370'),
(22, 'auth', '0004_alter_user_username_opts', '2026-04-04 00:08:09.911877'),
(23, 'auth', '0005_alter_user_last_login_null', '2026-04-04 00:08:09.923881'),
(24, 'auth', '0006_require_contenttypes_0002', '2026-04-04 00:08:09.926214'),
(25, 'auth', '0007_alter_validators_add_error_messages', '2026-04-04 00:08:09.931373'),
(26, 'auth', '0008_alter_user_username_max_length', '2026-04-04 00:08:09.941280'),
(27, 'auth', '0009_alter_user_last_name_max_length', '2026-04-04 00:08:09.950780'),
(28, 'auth', '0010_alter_group_name_max_length', '2026-04-04 00:08:09.959785'),
(29, 'auth', '0011_update_proxy_permissions', '2026-04-04 00:08:09.968707'),
(30, 'auth', '0012_alter_user_first_name_max_length', '2026-04-04 00:08:09.978579'),
(31, 'sessions', '0001_initial', '2026-04-04 00:08:09.989579');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_session`
--

CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `appprincipal_boleta`
--
ALTER TABLE `appprincipal_boleta`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `venta_id` (`venta_id`);

--
-- Indices de la tabla `appprincipal_carrito`
--
ALTER TABLE `appprincipal_carrito`
  ADD PRIMARY KEY (`id`),
  ADD KEY `appPrincipal_carrito_usuario_id_3cbf28de_fk_appPrinci` (`usuario_id`);

--
-- Indices de la tabla `appprincipal_devolucion`
--
ALTER TABLE `appprincipal_devolucion`
  ADD PRIMARY KEY (`id`),
  ADD KEY `appPrincipal_devoluc_producto_id_85856ca4_fk_appPrinci` (`producto_id`),
  ADD KEY `appPrincipal_devoluc_usuario_id_4ca389c6_fk_appPrinci` (`usuario_id`),
  ADD KEY `appPrincipal_devoluc_venta_id_2a9b1c77_fk_appPrinci` (`venta_id`);

--
-- Indices de la tabla `appprincipal_envio`
--
ALTER TABLE `appprincipal_envio`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `venta_id` (`venta_id`);

--
-- Indices de la tabla `appprincipal_favorito`
--
ALTER TABLE `appprincipal_favorito`
  ADD PRIMARY KEY (`id`),
  ADD KEY `appPrincipal_favorit_producto_id_e0cd3670_fk_appPrinci` (`producto_id`),
  ADD KEY `appPrincipal_favorit_usuario_id_ec4c3124_fk_appPrinci` (`usuario_id`);

--
-- Indices de la tabla `appprincipal_itemcarritoproducto`
--
ALTER TABLE `appprincipal_itemcarritoproducto`
  ADD PRIMARY KEY (`id`),
  ADD KEY `appPrincipal_itemcar_carrito_id_fd140a06_fk_appPrinci` (`carrito_id`),
  ADD KEY `appPrincipal_itemcar_producto_id_f6f9a776_fk_appPrinci` (`producto_id`);

--
-- Indices de la tabla `appprincipal_opinion`
--
ALTER TABLE `appprincipal_opinion`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `appPrincipal_opinion_usuario_id_producto_id_f9904218_uniq` (`usuario_id`,`producto_id`),
  ADD KEY `appPrincipal_opinion_producto_id_7cd6214d_fk_appPrinci` (`producto_id`);

--
-- Indices de la tabla `appprincipal_producto`
--
ALTER TABLE `appprincipal_producto`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `appprincipal_productoventa`
--
ALTER TABLE `appprincipal_productoventa`
  ADD PRIMARY KEY (`id`),
  ADD KEY `appPrincipal_product_producto_id_29685283_fk_appPrinci` (`producto_id`),
  ADD KEY `appPrincipal_product_venta_id_d5ea0264_fk_appPrinci` (`venta_id`);

--
-- Indices de la tabla `appprincipal_reclamo`
--
ALTER TABLE `appprincipal_reclamo`
  ADD PRIMARY KEY (`id`),
  ADD KEY `appPrincipal_reclamo_usuario_id_7e40b1ff_fk_appPrinci` (`usuario_id`),
  ADD KEY `appPrincipal_reclamo_venta_id_311556f5_fk_appPrincipal_venta_id` (`venta_id`);

--
-- Indices de la tabla `appprincipal_usuario`
--
ALTER TABLE `appprincipal_usuario`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `rut` (`rut`);

--
-- Indices de la tabla `appprincipal_venta`
--
ALTER TABLE `appprincipal_venta`
  ADD PRIMARY KEY (`id`),
  ADD KEY `appPrincipal_venta_carrito_id_d11473a4_fk_appPrinci` (`carrito_id`),
  ADD KEY `appPrincipal_venta_usuario_id_a424aa2e_fk_appPrinci` (`usuario_id`);

--
-- Indices de la tabla `auth_group`
--
ALTER TABLE `auth_group`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indices de la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  ADD KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`);

--
-- Indices de la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`);

--
-- Indices de la tabla `auth_user`
--
ALTER TABLE `auth_user`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indices de la tabla `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  ADD KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`);

--
-- Indices de la tabla `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  ADD KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`);

--
-- Indices de la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  ADD KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`);

--
-- Indices de la tabla `django_content_type`
--
ALTER TABLE `django_content_type`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`);

--
-- Indices de la tabla `django_migrations`
--
ALTER TABLE `django_migrations`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `django_session`
--
ALTER TABLE `django_session`
  ADD PRIMARY KEY (`session_key`),
  ADD KEY `django_session_expire_date_a5c62663` (`expire_date`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `appprincipal_boleta`
--
ALTER TABLE `appprincipal_boleta`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `appprincipal_carrito`
--
ALTER TABLE `appprincipal_carrito`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de la tabla `appprincipal_devolucion`
--
ALTER TABLE `appprincipal_devolucion`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `appprincipal_envio`
--
ALTER TABLE `appprincipal_envio`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `appprincipal_favorito`
--
ALTER TABLE `appprincipal_favorito`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `appprincipal_itemcarritoproducto`
--
ALTER TABLE `appprincipal_itemcarritoproducto`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de la tabla `appprincipal_opinion`
--
ALTER TABLE `appprincipal_opinion`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `appprincipal_producto`
--
ALTER TABLE `appprincipal_producto`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de la tabla `appprincipal_productoventa`
--
ALTER TABLE `appprincipal_productoventa`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `appprincipal_reclamo`
--
ALTER TABLE `appprincipal_reclamo`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `appprincipal_usuario`
--
ALTER TABLE `appprincipal_usuario`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `appprincipal_venta`
--
ALTER TABLE `appprincipal_venta`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_group`
--
ALTER TABLE `auth_group`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=73;

--
-- AUTO_INCREMENT de la tabla `auth_user`
--
ALTER TABLE `auth_user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `django_content_type`
--
ALTER TABLE `django_content_type`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT de la tabla `django_migrations`
--
ALTER TABLE `django_migrations`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=32;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `appprincipal_boleta`
--
ALTER TABLE `appprincipal_boleta`
  ADD CONSTRAINT `appPrincipal_boleta_venta_id_937bbb72_fk_appPrincipal_venta_id` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`);

--
-- Filtros para la tabla `appprincipal_carrito`
--
ALTER TABLE `appprincipal_carrito`
  ADD CONSTRAINT `appPrincipal_carrito_usuario_id_3cbf28de_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`);

--
-- Filtros para la tabla `appprincipal_devolucion`
--
ALTER TABLE `appprincipal_devolucion`
  ADD CONSTRAINT `appPrincipal_devoluc_producto_id_85856ca4_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  ADD CONSTRAINT `appPrincipal_devoluc_usuario_id_4ca389c6_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`),
  ADD CONSTRAINT `appPrincipal_devoluc_venta_id_2a9b1c77_fk_appPrinci` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`);

--
-- Filtros para la tabla `appprincipal_envio`
--
ALTER TABLE `appprincipal_envio`
  ADD CONSTRAINT `appPrincipal_envio_venta_id_ce3fcdfe_fk_appPrincipal_venta_id` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`);

--
-- Filtros para la tabla `appprincipal_favorito`
--
ALTER TABLE `appprincipal_favorito`
  ADD CONSTRAINT `appPrincipal_favorit_producto_id_e0cd3670_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  ADD CONSTRAINT `appPrincipal_favorit_usuario_id_ec4c3124_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`);

--
-- Filtros para la tabla `appprincipal_itemcarritoproducto`
--
ALTER TABLE `appprincipal_itemcarritoproducto`
  ADD CONSTRAINT `appPrincipal_itemcar_carrito_id_fd140a06_fk_appPrinci` FOREIGN KEY (`carrito_id`) REFERENCES `appprincipal_carrito` (`id`),
  ADD CONSTRAINT `appPrincipal_itemcar_producto_id_f6f9a776_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`);

--
-- Filtros para la tabla `appprincipal_opinion`
--
ALTER TABLE `appprincipal_opinion`
  ADD CONSTRAINT `appPrincipal_opinion_producto_id_7cd6214d_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  ADD CONSTRAINT `appPrincipal_opinion_usuario_id_a6b8154e_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`);

--
-- Filtros para la tabla `appprincipal_productoventa`
--
ALTER TABLE `appprincipal_productoventa`
  ADD CONSTRAINT `appPrincipal_product_producto_id_29685283_fk_appPrinci` FOREIGN KEY (`producto_id`) REFERENCES `appprincipal_producto` (`id`),
  ADD CONSTRAINT `appPrincipal_product_venta_id_d5ea0264_fk_appPrinci` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`);

--
-- Filtros para la tabla `appprincipal_reclamo`
--
ALTER TABLE `appprincipal_reclamo`
  ADD CONSTRAINT `appPrincipal_reclamo_usuario_id_7e40b1ff_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`),
  ADD CONSTRAINT `appPrincipal_reclamo_venta_id_311556f5_fk_appPrincipal_venta_id` FOREIGN KEY (`venta_id`) REFERENCES `appprincipal_venta` (`id`);

--
-- Filtros para la tabla `appprincipal_venta`
--
ALTER TABLE `appprincipal_venta`
  ADD CONSTRAINT `appPrincipal_venta_carrito_id_d11473a4_fk_appPrinci` FOREIGN KEY (`carrito_id`) REFERENCES `appprincipal_carrito` (`id`),
  ADD CONSTRAINT `appPrincipal_venta_usuario_id_a424aa2e_fk_appPrinci` FOREIGN KEY (`usuario_id`) REFERENCES `appprincipal_usuario` (`id`);

--
-- Filtros para la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);

--
-- Filtros para la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

--
-- Filtros para la tabla `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  ADD CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Filtros para la tabla `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  ADD CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  ADD CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Filtros para la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
