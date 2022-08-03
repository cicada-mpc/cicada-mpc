Feature: MPC Calculator Service

    @calculator
    Scenario Outline: Addition
        Given a calculator service with <players> players
        When the players raise <exception>
        Then the returned exceptions should match <exception>

        Examples:
        | players | exception                 |
        | 2       | RuntimeError("foo")       |
