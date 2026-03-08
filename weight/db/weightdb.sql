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

-------------------
-----MOCK DATA-----
-------------------

USE weight;

-- Clean up existing data for a fresh test
TRUNCATE TABLE containers_registered;
TRUNCATE TABLE transactions;

-- --------------------------------------------------------
-- 1. Mock Containers
-- --------------------------------------------------------
INSERT INTO containers_registered (container_id, weight, unit) VALUES
('C-101', 500, 'kg'),   -- Standard kg container
('C-102', 1000, 'lbs'), -- lbs container (should convert to ~453 kg)
('C-103', NULL, NULL);  -- Container with unknown tara

-- --------------------------------------------------------
-- 2. Mock Transactions
-- Note: Assuming today is in March 2026 for the default date filters.
-- --------------------------------------------------------

-- Session 1: Truck T-123 (Happened THIS month: March 5, 2026)
INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce, session_id) VALUES
('2026-03-05 10:00:00', 'in', 'T-123', 'C-101,C-102', 15000, NULL, NULL, 'orange', 1),
('2026-03-05 11:00:00', 'out', 'T-123', 'C-101,C-102', 15000, 5000, 9047, 'orange', 1);

-- Session 2: Truck T-123 (Happened LAST month: Feb 20, 2026 - should be filtered out by default dates)
INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce, session_id) VALUES
('2026-02-20 08:00:00', 'in', 'T-123', 'C-103', 12000, NULL, NULL, 'tomato', 2),
('2026-02-20 09:00:00', 'out', 'T-123', 'C-103', 12000, 5200, NULL, 'tomato', 2);

-- Session 3: Truck T-999 (Happened THIS month: March 6, 2026 - currently inside the factory, no 'out' yet)
INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce, session_id) VALUES
('2026-03-06 12:00:00', 'in', 'T-999', 'C-101', 10000, NULL, NULL, 'apple', 3);

show tables;

describe containers_registered;
describe transactions;