-- Legacy RADIUS manager user creation removed.
-- WireGuard tables will be managed by SQLAlchemy models (WireGuardPeer).
-- Added for schema reference and initial setup.
CREATE TABLE IF NOT EXISTS `wireguard_peer` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `peer_number` int(11) NOT NULL,
  `private_key` varchar(44) NOT NULL,
  `public_key` varchar(44) NOT NULL,
  `preshared_key` varchar(44) NOT NULL,
  `ip_address` varchar(40) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `wireguard_peer_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
