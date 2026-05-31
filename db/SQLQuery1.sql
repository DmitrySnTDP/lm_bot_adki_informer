use lm_bot_db;
go

alter table LocalTarget
add
	constraint FK_LocalTarget_Users foreign key (UserID) references Users(UserID),
	constraint FK_LocalTarget_Settings foreign key (SetID) references Settings(SetID);

go

alter table GroupTarget
add
	constraint FK_GroupTarget_Users foreign key (UserID) references Users(UserID),
	constraint FK_GroupTarget_Settings foreign key (SetID) references Settings(SetID);
go

alter table SettingsEvent
add
	constraint FK_SettingsEvent_Settings foreign key (SetID) references Settings(SetID),
	constraint FK_SettingsEvent_EventType foreign key (EventID) references EventType(EventID),
	constraint FK_SettingsEvent_Medal foreign key (MedID) references Medal(MedID);
go


DBCC CHECKIDENT ('SettingsEvent', RESEED, 0);
go



CREATE TRIGGER TrigSettingsProtectDefault
ON Settings
INSTEAD OF UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM deleted WHERE SetID = 1)
    BEGIN
        PRINT('SetID = 1 (настройки по умолчанию) нельзя изменять или удалять');
        ROLLBACK;
        RETURN;
    END;
    IF EXISTS (SELECT 1 FROM inserted)
        UPDATE s SET IsDefault = i.IsDefault
        FROM Settings s JOIN inserted i ON s.SetID = i.SetID;
    IF EXISTS (SELECT 1 FROM deleted)
        DELETE FROM Settings WHERE SetID IN (SELECT SetID FROM deleted);
END;
GO


CREATE TRIGGER TrigSettingsEventProtectDefault
ON SettingsEvent
INSTEAD OF INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM inserted WHERE SetID = 1)
       OR EXISTS (SELECT 1 FROM deleted WHERE SetID = 1)
    BEGIN
        PRINT('Изменение SettingsEvent для SetID = 1 запрещено');
        ROLLBACK;
        RETURN;
    END;

    IF EXISTS (SELECT 1 FROM deleted)
        DELETE FROM SettingsEvent
        WHERE SetID IN (SELECT SetID FROM deleted)
          AND EventID IN (SELECT EventID FROM deleted)
          AND MedID IN (SELECT MedID FROM deleted);
    IF EXISTS (SELECT 1 FROM inserted)
        INSERT INTO SettingsEvent (SetID, EventID, MedID)
        SELECT SetID, EventID, MedID FROM inserted;
END;
GO

CREATE TYPE dbo.EventIDList AS TABLE (EventID INT NOT NULL PRIMARY KEY);
GO


CREATE PROCEDURE dbo.SetLocalTargetSettings
    @UserID      INT,
    @MedalID     INT,
    @EventIDs    dbo.EventIDList READONLY
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @CurrentSetID INT, @NewSetID INT;

    SELECT @CurrentSetID = SetID FROM LocalTarget WHERE UserID = @UserID;
    IF @CurrentSetID IS NULL
    BEGIN
        RAISERROR('Цель пользователя не найдена', 16, 1);
        RETURN;
    END;

    IF @CurrentSetID = 1
    BEGIN
        SELECT @NewSetID = ISNULL(MAX(SetID), 0) + 1 FROM Settings;
        INSERT INTO Settings (SetID, IsDefault) VALUES (@NewSetID, 0);
        INSERT INTO SettingsEvent (SetID, EventID, MedID)
        SELECT @NewSetID, EventID, MedID FROM SettingsEvent WHERE SetID = 1;
        UPDATE LocalTarget SET SetID = @NewSetID WHERE UserID = @UserID;
        SET @CurrentSetID = @NewSetID;
    END;

    DELETE FROM SettingsEvent
    WHERE SetID = @CurrentSetID AND MedID = @MedalID;

    INSERT INTO SettingsEvent (SetID, EventID, MedID)
    SELECT @CurrentSetID, EventID, @MedalID FROM @EventIDs;
END;
GO


CREATE PROCEDURE dbo.SetGroupTargetSettings
    @GroupID     INT,
    @MedalID     INT,
    @EventIDs    dbo.EventIDList READONLY
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @CurrentSetID INT, @NewSetID INT;

    SELECT @CurrentSetID = SetID FROM GroupTarget WHERE GroupID = @GroupID;
    IF @CurrentSetID IS NULL
    BEGIN
        RAISERROR('Групповая цель не найдена', 16, 1);
        RETURN;
    END;

    IF @CurrentSetID = 1
    BEGIN
        SELECT @NewSetID = ISNULL(MAX(SetID), 0) + 1 FROM Settings;
        INSERT INTO Settings (SetID, IsDefault) VALUES (@NewSetID, 0);
        INSERT INTO SettingsEvent (SetID, EventID, MedID)
        SELECT @NewSetID, EventID, MedID FROM SettingsEvent WHERE SetID = 1;
        UPDATE GroupTarget SET SetID = @NewSetID WHERE GroupID = @GroupID;
        SET @CurrentSetID = @NewSetID;
    END;

    DELETE FROM SettingsEvent WHERE SetID = @CurrentSetID AND MedID = @MedalID;
    INSERT INTO SettingsEvent (SetID, EventID, MedID)
    SELECT @CurrentSetID, EventID, @MedalID FROM @EventIDs;
END;
GO


CREATE PROCEDURE dbo.ResetLocalTargetToDefault
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @SetID INT = (SELECT SetID FROM LocalTarget WHERE UserID = @UserID);
    IF @SetID IS NULL OR @SetID = 1
    BEGIN
        PRINT('Цель не найдена или уже использует настройки по умолчанию');
        RETURN;
    END;

    DELETE FROM SettingsEvent WHERE SetID = @SetID;

    INSERT INTO SettingsEvent (SetID, EventID, MedID)
    SELECT @SetID, EventID, MedID FROM SettingsEvent WHERE SetID = 1;
END;
GO


CREATE PROCEDURE dbo.ResetGroupTargetToDefault
    @GroupID INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @SetID INT = (SELECT SetID FROM GroupTarget WHERE GroupID = @GroupID);
    IF @SetID IS NULL OR @SetID = 1
    BEGIN
        PRINT('Групповая цель не найдена или уже использует настройки по умолчанию');
        RETURN;
    END;
    DELETE FROM SettingsEvent WHERE SetID = @SetID;
    INSERT INTO SettingsEvent (SetID, EventID, MedID)
    SELECT @SetID, EventID, MedID FROM SettingsEvent WHERE SetID = 1;
END;
GO


-- Вспомогательная процедура для удаления SetID, если он не используется
CREATE PROCEDURE dbo.CleanupUnusedSetID
    @SetID INT
AS
BEGIN
    IF @SetID = 1 RETURN;
    IF NOT EXISTS (SELECT 1 FROM LocalTarget WHERE SetID = @SetID)
       AND NOT EXISTS (SELECT 1 FROM GroupTarget WHERE SetID = @SetID)
    BEGIN
        DELETE FROM SettingsEvent WHERE SetID = @SetID;
        DELETE FROM Settings WHERE SetID = @SetID;
    END;
END;
GO

-- Триггер на удаление из LocalTarget
CREATE TRIGGER TrigLocalTargetDeleteCleanup
ON LocalTarget
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @SetID INT;
    DECLARE cur CURSOR FOR SELECT DISTINCT SetID FROM deleted WHERE SetID != 1;
    OPEN cur;
    FETCH NEXT FROM cur INTO @SetID;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        EXEC dbo.CleanupUnusedSetID @SetID;
        FETCH NEXT FROM cur INTO @SetID;
    END;
    CLOSE cur;
    DEALLOCATE cur;
END;
GO

-- Триггер на удаление из GroupTarget
CREATE TRIGGER TrigGroupTargetDeleteCleanup
ON GroupTarget
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @SetID INT;
    DECLARE cur CURSOR FOR SELECT DISTINCT SetID FROM deleted WHERE SetID != 1;
    OPEN cur;
    FETCH NEXT FROM cur INTO @SetID;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        EXEC dbo.CleanupUnusedSetID @SetID;
        FETCH NEXT FROM cur INTO @SetID;
    END;
    CLOSE cur;
    DEALLOCATE cur;
END;
GO


CREATE PROCEDURE dbo.GetTargetsByMedalAndEvent
    @MedalID INT,
    @EventID INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT 
        'Local' AS TargetType,
        lt.UserID AS TargetID,
        lt.IsActive
    FROM LocalTarget lt
    JOIN SettingsEvent se ON lt.SetID = se.SetID
    WHERE se.MedID = @MedalID AND se.EventID = @EventID
      AND lt.IsActive = 1

    UNION ALL

    SELECT 
        'Group' AS TargetType,
        gt.GroupID AS TargetID,
        gt.IsActive
    FROM GroupTarget gt
    JOIN SettingsEvent se ON gt.SetID = se.SetID
    WHERE se.MedID = @MedalID AND se.EventID = @EventID
      AND gt.IsActive = 1;
END;
GO


CREATE TRIGGER TrigLocalTargetUpdateTargetCount
ON LocalTarget
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @UserIDs TABLE (UserID INT PRIMARY KEY);
    INSERT INTO @UserIDs (UserID)
    SELECT UserID FROM inserted
    UNION
    SELECT UserID FROM deleted;
    
    UPDATE u
    SET TargetCount = ISNULL(l.cnt, 0) + ISNULL(g.cnt, 0)
    FROM Users u
    LEFT JOIN (SELECT UserID, COUNT(*) AS cnt FROM LocalTarget GROUP BY UserID) l 
        ON u.UserID = l.UserID
    LEFT JOIN (SELECT UserID, COUNT(*) AS cnt FROM GroupTarget GROUP BY UserID) g 
        ON u.UserID = g.UserID
    WHERE u.UserID IN (SELECT UserID FROM @UserIDs);
END;
GO


CREATE TRIGGER TrigGroupTargetUpdateTargetCount
ON GroupTarget
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @UserIDs TABLE (UserID INT PRIMARY KEY);
    INSERT INTO @UserIDs (UserID)
    SELECT UserID FROM inserted
    UNION
    SELECT UserID FROM deleted;
    
    UPDATE u
    SET TargetCount = ISNULL(l.cnt, 0) + ISNULL(g.cnt, 0)
    FROM Users u
    LEFT JOIN (SELECT UserID, COUNT(*) AS cnt FROM LocalTarget GROUP BY UserID) l 
        ON u.UserID = l.UserID
    LEFT JOIN (SELECT UserID, COUNT(*) AS cnt FROM GroupTarget GROUP BY UserID) g 
        ON u.UserID = g.UserID
    WHERE u.UserID IN (SELECT UserID FROM @UserIDs);
END;
GO


insert into LocalTarget (UserID, SetID)
values (12345, 1);
go
update SettingsEvent
set SetID = 2
where SetEvID = 15;
go

--insert into Settings (IsDefault) values (1);


-- 6.1 Текстовая статистика
CREATE PROCEDURE dbo.GetStatisticsText
AS
BEGIN
    DECLARE @TotalUsers INT = (SELECT COUNT(*) FROM Users);
    DECLARE @TotalLocalTargets INT = (SELECT COUNT(*) FROM LocalTarget);
    DECLARE @TotalGroupTargets INT = (SELECT COUNT(*) FROM GroupTarget);
    SELECT CONCAT(
        'Всего пользователей: ', @TotalUsers, CHAR(13),
        'Личных целей: ', @TotalLocalTargets, CHAR(13),
        'Групповых целей: ', @TotalGroupTargets
    ) AS StatisticsText;
END;
GO

-- 6.2 Таблица: пользователь -> количество активных целей
CREATE PROCEDURE dbo.GetUserActiveTargets
AS
BEGIN
    SELECT 
        u.UserID,
        COALESCE(l.ActiveLocal, 0) + COALESCE(g.ActiveGroup, 0) AS ActiveTargetCount
    FROM Users u
    LEFT JOIN (
        SELECT UserID, COUNT(*) AS ActiveLocal
        FROM LocalTarget
        WHERE IsActive = 1
        GROUP BY UserID
    ) l ON u.UserID = l.UserID
    LEFT JOIN (
        SELECT UserID, COUNT(*) AS ActiveGroup
        FROM GroupTarget
        WHERE IsActive = 1
        GROUP BY UserID
    ) g ON u.UserID = g.UserID;
END;
GO


exec GetStatisticsText
go
exec GetUserActiveTargets
go

delete from LocalTarget
where UserID=12345;
go
delete from Users
where UserID = 12345;
go


insert into Users (UserID) values (1) where (select * from Users where UserID = 1) = 0;

select * from Users
select * from LocalTarget
select * from GroupTarget
select * from Settings
select * from SettingsEvent

insert into LocalTarget (UserID) values (8361667826)

update LocalTarget set IsActive = ~IsActive where UserID = 8361667826 

update GroupTarget set IsActive = ~IsActive where GroupName = ?  call.data.split("__")[-1]

select IsActive from LocalTarget where UserID = 5314192316

insert into Users (UserID) values (5314192316) where (select from Users where UserID == user_id) == None 


GRANT EXECUTE ON TYPE::dbo.EventIDList TO lm_bot_localhost;
GRANT EXECUTE ON dbo.SetLocalTargetSettings TO lm_bot_localhost;
GRANT EXECUTE ON dbo.SetGroupTargetSettings TO lm_bot_localhost;
GRANT EXECUTE ON dbo.ResetLocalTargetToDefault TO lm_bot_localhost;
GRANT EXECUTE ON dbo.ResetGroupTargetToDefault TO lm_bot_localhost;
GRANT EXECUTE ON dbo.GetTargetsByMedalAndEvent TO lm_bot_localhost;


select * from Medal
select MedID from Medal where MedName = ''

exec GetTargetsByMedalAndEvent 3, 3