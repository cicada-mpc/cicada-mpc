Feature: MPC Calculator Service

    @calculator
    Scenario: Unix Domain Sockets
        Given a calculator service with 3 players using unix domain sockets
        And public value 4
        Then the players can retrieve a complete copy of the operand stack


    @calculator
    Scenario Outline: Exception Handling
        Given a calculator service with <players> players
        When the players raise <exception>
        Then the returned exceptions should match <exception>

        Examples:
        | players | exception                 |
        | 2       | RuntimeError("foo")       |



    @calculator
    Scenario Outline: Operand Stack
        Given a calculator service with <players> players
        And public value <a>
        And public value <b>
        Then the players can retrieve a complete copy of the operand stack
        And the stack should match <stack> for all players

        Examples:
        | players | a   | b     | stack                 |
        | 3       | 3   | "foo" | [3, "foo"]            |

