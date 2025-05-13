DELIMITER //

-- Eliminar el procedimiento si ya existe
DROP PROCEDURE IF EXISTS buscar_columnas_urls;

CREATE PROCEDURE buscar_columnas_urls(IN db_name VARCHAR(64), IN dominio_correcto VARCHAR(255))
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE tbl_name VARCHAR(64);
    DECLARE col_name VARCHAR(64);

    -- Lista de palabras clave de MySQL
    DECLARE reserved_keywords TEXT DEFAULT 'SELECT,INSERT,UPDATE,DELETE,FROM,WHERE,JOIN,ORDER,BY,CREATE,ALTER,DROP,INDEX,LIKE,AND,OR,NOT,NULL,AS,DESC,KEY';

    -- Cursor para iterar sobre las columnas
    DECLARE cur CURSOR FOR 
        SELECT TABLE_NAME, COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = db_name 
        AND DATA_TYPE IN ('varchar', 'text')
        AND FIND_IN_SET(UPPER(COLUMN_NAME), reserved_keywords) = 0;
    
    -- Manejador para el final del cursor
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    -- Abrir el cursor
    OPEN cur;

    read_loop: LOOP
        -- Obtener los datos del cursor
        FETCH cur INTO tbl_name, col_name;

        IF done THEN
            LEAVE read_loop;
        END IF;

        -- Construir el query dinámico
        SET @query = CONCAT('SELECT ', col_name, 
                           ' FROM ', db_name, '.', tbl_name, 
                           ' WHERE ', col_name, ' IS NOT NULL',
                           ' AND ', col_name, ' LIKE ''http://%/uploads/%''',
                           ' AND ', col_name, ' NOT LIKE ''http://', dominio_correcto, '/uploads/%'''
        );

        -- SELECT @query;
        -- Preparar y ejecutar la consulta
        PREPARE stmt FROM @query;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;

    END LOOP;

    -- Cerrar el cursor
    CLOSE cur;
END //


-- Eliminar el procedimiento si ya existe
DROP PROCEDURE IF EXISTS buscar_y_actualizar_urls;

CREATE PROCEDURE buscar_y_actualizar_urls(IN db_name VARCHAR(64), IN dominio_correcto VARCHAR(255))
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE tbl_name VARCHAR(64);
    DECLARE col_name VARCHAR(64);

    -- Lista de palabras clave de MySQL
    DECLARE reserved_keywords TEXT DEFAULT 'SELECT,INSERT,UPDATE,DELETE,FROM,WHERE,JOIN,ORDER,BY,CREATE,ALTER,DROP,INDEX,LIKE,AND,OR,NOT,NULL,AS,DESC,KEY';

    -- Cursor para iterar sobre las columnas
    DECLARE cur CURSOR FOR 
        SELECT TABLE_NAME, COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = db_name 
        AND DATA_TYPE IN ('varchar', 'text')
        AND FIND_IN_SET(UPPER(COLUMN_NAME), reserved_keywords) = 0;
    
    -- Manejador para el final del cursor
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    -- Abrir el cursor
    OPEN cur;

    read_loop: LOOP
        -- Obtener los datos del cursor
        FETCH cur INTO tbl_name, col_name;

        IF done THEN
            LEAVE read_loop;
        END IF;

        -- Construir el query dinámico para seleccionar y actualizar
        SET @query = CONCAT('UPDATE ', db_name, '.', tbl_name,
                            ' SET ', col_name, ' = REPLACE(', col_name, 
                            ', SUBSTRING_INDEX(', col_name, ', ''/uploads/'', 1), ''http://', dominio_correcto, ''')',
                            ' WHERE ', col_name, ' IS NOT NULL',
                            ' AND ', col_name, ' LIKE ''http://%/uploads/%''',
                            ' AND ', col_name, ' NOT LIKE ''http://', dominio_correcto, '/uploads/%''');

        -- Ejecutar el UPDATE dinámico
        PREPARE stmt FROM @query;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;

    END LOOP;

    -- Cerrar el cursor
    CLOSE cur;
END //

DELIMITER ;