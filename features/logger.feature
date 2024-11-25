Feature: Logging

    Scenario: Logger Attribute
        Given 3 players
        When the players create a Cicada logger, they can access the underlying Python logger


    Scenario: Change Sync Permanently
        Given 3 players
        When the players create a Cicada logger, they can change the sync attribute


    Scenario: Change Sync Temporarily
        Given 3 players
        When the players create a Cicada logger, they can temporarily change the sync attribute


    Scenario Outline: Message Logging
        Given <players> players
        When the players log <message> with level <level> and src <src>, the message is logged correctly

        Examples:
        | players | message | level            | src       |
        | 2       | "foo"   | logging.DEBUG    | None      |
        | 3       | "bar"   | logging.INFO     | 0         |
        | 4       | "blah"  | logging.WARNING  | [1]       |
        | 5       | "bleh"  | logging.ERROR    | [2, 3]    |
        | 6       | "bleh"  | logging.CRITICAL | None      |
