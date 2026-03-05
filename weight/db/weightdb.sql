--
-- Database: `Weight`
--

CREATE DATABASE IF NOT EXISTS `weight`;

-- --------------------------------------------------------

--
-- Table structure for table `containers-registered`
--

USE weight;

CREATE TABLE IF NOT EXISTS `containers_registered` (
  `container_id` varchar(15) NOT NULL,
  `weight` int DEFAULT NULL,
  `unit` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`container_id`)
) ENGINE=MyISAM AUTO_INCREMENT=10001 ;

-- --------------------------------------------------------

--
-- Table structure for table `transactions`
--

CREATE TABLE IF NOT EXISTS `transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `datetime` datetime DEFAULT NULL,
  `direction` varchar(10) DEFAULT NULL,
  `truck` varchar(50) DEFAULT NULL,
  `containers` varchar(10000) DEFAULT NULL,
  `bruto` int DEFAULT NULL,
  `truckTara` int DEFAULT NULL,
  `neto` int DEFAULT NULL,
  `produce` varchar(50) DEFAULT NULL,
  `session_id` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=10001;

show tables;

describe containers_registered;
describe transactions;



--
-- Dumping data for table `test`
--

-- INSERT INTO `test` (`id`, `aa`) VALUES
-- (1, 'aaaa'),
