Feature: MPC as a Service

    @wip
    Scenario Outline: Addition
        Given an MPC service with world size <players>
        And an AdditiveProtocol object
        When player 0 secret shares operand <a>
        And player 1 secret shares operand <b>
        And all players use private-private addition
        And all players reveal the result
        Then the result should be <result>

        Examples:
        | players | a  | b    | result  |
        | 2       | 2  | 3    | 5       |
