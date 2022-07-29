Feature: MPC as a Service

    @calculator
    Scenario Outline: Addition
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        When player 0 secret shares <a>
        And player 1 secret shares <b>
        And the players add the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a  | b    | result  |
        | 2       | 2  | 3    | 5       |
