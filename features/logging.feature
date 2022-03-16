Feature: Logging

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
