-- Billing DB
CREATE DATABASE IF NOT EXISTS billdb;
USE billdb;

-- Provider: name should be unique and not null
CREATE TABLE IF NOT EXISTS Provider (
  id   INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_provider_name (name)
) ENGINE=InnoDB AUTO_INCREMENT=10001;

-- Trucks: belongs to a provider
CREATE TABLE IF NOT EXISTS Trucks (
  id          VARCHAR(10) NOT NULL,
  provider_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_trucks_provider
    FOREIGN KEY (provider_id) REFERENCES Provider(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Rates:
-- scope is either 'ALL' or a provider id stored as text (e.g. '10001')
-- We DO NOT use a foreign key here because scope can be 'ALL'.
CREATE TABLE IF NOT EXISTS Rates (
  product_id VARCHAR(50) NOT NULL,
  rate       INT NOT NULL DEFAULT 0,
  scope      VARCHAR(50) NOT NULL,
  PRIMARY KEY (product_id, scope)
) ENGINE=InnoDB;

