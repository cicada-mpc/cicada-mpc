Feature: MPC as a Service

    Scenario Outline: Addition
        Given an MPC service with world size <players>
        And an AdditiveProtocol object
        When player 0 secret shares operand <a>
        And player 1 secret shares operand <b>
        And all players add the operands
        And all players reveal the result
        Then the result should match <result>

        Examples:
        | players | a  | b    | result  |
        | 2       | 2  | 3    | 5       |
