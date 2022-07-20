Feature: Logging

    Scenario: Logger attribute
        Given 3 players
        When the players create a Cicada logger, they can access the underlying Python logger


    Scenario: Override logger sync
        Given 3 players
        When the players create a Cicada logger, they can temporarily override the sync attribute


    Scenario Outline: Logging
        Given <players> players
        When the players log <message> with level <level>, the message is logged at the correct level

        Examples:
        | players | message | level            |
        | 2       | "foo"   | logging.DEBUG    |
        | 3       | "bar"   | logging.INFO     |
        | 4       | "blah"  | logging.WARNING  |
        | 5       | "bleh"  | logging.ERROR    |
        | 6       | "bleh"  | logging.CRITICAL |
