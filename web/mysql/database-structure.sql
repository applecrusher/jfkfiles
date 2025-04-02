CREATE TABLE `documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `document_id` varchar(100) DEFAULT NULL,
  `total_pages` int DEFAULT NULL,
  `original_url` varchar(2048) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `document_id` (`document_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2342 DEFAULT CHARSET=utf8mb3


CREATE TABLE `pages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `document_id` int DEFAULT NULL,
  `page_number` int DEFAULT NULL,
  `text` longtext,
  PRIMARY KEY (`id`),
  KEY `document_id` (`document_id`),
  FULLTEXT KEY `text` (`text`),
  CONSTRAINT `pages_ibfk_1` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=78605 DEFAULT CHARSET=utf8mb3