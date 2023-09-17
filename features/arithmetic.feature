Feature: Arithmetic

    Scenario Outline: Field Array
        Given a <field>
        And a field array <a>
        Then the field array should match <b>

        Examples:
        | field                | a                  | b                  |
        | default Field        | 1                  | 1                  |
        | default Field        | [1]                | [1]                |
        | default Field        | [1,2,3]            | [1,2,3]            |
        | default Field        | [[1,2,3],[4,5,6]]  | [[1,2,3],[4,5,6]]  |
        | Field with order 251 | -1                 | 250                |
        | Field with order 251 | 252                | 1                  |


    Scenario Outline: Field Array Addition
        Given a <field>
        And a field array <a>
        And a field array <b>
        When the second field array is added to the first
        Then the field array should match <c>

        Examples:
        | field          | a         | b         | c        |
        | default Field  | 1         | 1         | 2        |
        | default Field  | 1         | 3         | 4        |
        | default Field  | 1         | 0         | 1        |
        | default Field  | 0         | 1         | 1        |
        | default Field  | -1        | 1         | 0        |


    Scenario Outline: Field Array In-Place Addition
        Given a <field>
        And a field array <a>
        And a field array <b>
        When the second field array is added in-place to the first
        Then the field array should match <c>

        Examples:
        | field          | a         | b         | c        |
        | default Field  | 1         | 1         | 2        |
        | default Field  | 1         | 3         | 4        |
        | default Field  | 1         | 0         | 1        |
        | default Field  | 0         | 1         | 1        |
        | default Field  | -1        | 1         | 0        |


    Scenario Outline: Field Array In-Place Subtraction
        Given a <field>
        And a field array <a>
        And a field array <b>
        When the second field array is subtracted in-place from the first
        Then the field array should match <c>

        Examples:
        | field          | a         | b         | c        |
        | default Field  | 1         | 1         | 0        |
        | default Field  | 1         | 3         | -2       |
        | default Field  | 1         | 0         | 1        |
        | default Field  | 0         | 1         | -1       |


    Scenario Outline: Field Array Negation
        Given a <field>
        And a field array <a>
        When the field array is negated
        Then the field array should match <b>

        Examples:
        | field                     | a         | b                  |
        | Field with order 251      | 0         | 0                  |
        | Field with order 251      | 1         | 250                |
        | Field with order 251      | 3         | 248                |
        | Field with order 251      | -1        | 1                  |
        | Field with order 251      | -3        | 3                  |
        | Field with order 251      | [1, 2]    | [250, 249]         |


    Scenario Outline: Field Array Subtraction
        Given a <field>
        And a field array <a>
        And a field array <b>
        When the second field array is subtracted from the first
        Then the field array should match <c>

        Examples:
        | field          | a         | b         | c        |
        | default Field  | 1         | 1         | 0        |
        | default Field  | 1         | 3         | -2       |
        | default Field  | 1         | 0         | 1        |
        | default Field  | 0         | 1         | -1       |


    Scenario Outline: Field Array Summation
        Given a <field>
        And a field array <a>
        When the field array is summed
        Then the field array should match <b>

        Examples:
        | field          | a         | b         |
        | default Field  | [1, 2, 3] | 6         |


    Scenario Outline: Field Equality
        Given a <lhs>
        And a <rhs>
        Then the fields should compare <result>

        Examples:
        | lhs            | rhs                              | result   |
        | default Field  | default Field         | equal    |
        | default Field  | Field with order 251             | unequal  |


    Scenario Outline: Field Primality
        When a field with order <order> is created, it <outcome>

        Examples:
        | order          | outcome                       |
        | None           | should not raise an exception |
        | 251            | should not raise an exception |
        | 7              | should not raise an exception |
        | -251           | should raise an exception     |
        | 7.1            | should raise an exception     |
        | 4              | should raise an exception     |
        | 256            | should raise an exception     |


    Scenario Outline: Field Uniform Random
        Given a <field>
        When generating a field array of uniform random values with shape <shape>
        Then the field array shape should match <shape>
        And the field array values should be in-range for the field

        Examples:
        | field                | shape              |
        | default Field        | ()                 |
        | default Field        | (1,)               |
        | default Field        | (2, 3)             |


    Scenario Outline: Field Zeros
        Given a <field>
        When generating a field array of zeros with shape <shape>
        Then the field array should match <result>

        Examples:
        | field                | shape              | result                |
        | default Field        | ()                 | 0                     |
        | default Field        | 1                  | [0]                   |
        | default Field        | (2, 3)             | [[0, 0, 0],[0, 0, 0]] |


    Scenario Outline: Field Zeros Like
        Given a <field>
        When generating a field array of zeros like <other>
        Then the field array should match <result>

        Examples:
        | field          | other              | result                |
        | default Field  | 3                  | 0                     |
        | default Field  | [3, 4]             | [0, 0]                |
        | default Field  | [[3,4,5],[5,6,7]]  | [[0, 0, 0],[0, 0, 0]] |


