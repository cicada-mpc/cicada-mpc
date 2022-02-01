Feature: Interactive Programs

    Scenario Outline: Secret Input
        Given <players> players
        When player <player> receives secret input <input>
        Then the group should return <result>

        Examples:
        | players |  player | input     | result                     |
        | 1       |  0      | "1.2"     | [1.2]                      |
        | 2       |  0      | "1.2"     | [1.2, None]                |
        | 2       |  1      | "1.2"     | [None, 1.2]                |
        | 3       |  1      | "-5"      | [None, -5, None]           |
        | 4       |  2      | "-13.7"   | [None, None, -13.7, None]  |


