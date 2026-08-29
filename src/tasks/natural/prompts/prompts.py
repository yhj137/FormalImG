prompts_generate = """
You are an expert proficient in First-Order Logic (FOL) and Computer Vision scene synthesis. Your core task is to generate high-quality data pairs describing visual scenes based on a given vocabulary and logical constraints. Your input and output must be in strict JSON format.

#### Core Concept Definitions

*   **Dependency Closure**: A DSL expression can be decomposed into multiple top-level logical units connected by `(and ...)`. A logical closure is a minimal set of quantified variables connected to each other via binary predicates (such as `Holding`, `On`, `LeftOf`). Connectivity is transitive.
*   **Dependency Depth**: **Dependency Depth** is defined as **the total number of quantified variables (introduced by `exists`, `forall`) within a single logical closure**. The dependency depth of the entire DSL expression is the maximum dependency depth among all its logical closures.
*   **Scene Style**: Describes the overall artistic style or rendering method of the image. If a style is specified in the input parameters, the `IsStyle` predicate must be used in the DSL to declare it.

#### DSL Domain Definition
You must strictly adhere to the complete syntax and vocabulary of the following DSL and cannot create words outside the vocabulary. In our setting, all directions are relative to the frame.
{dsl}


#### Few-shot Examples

Below are compliant examples. Please pay attention to their JSON structure, especially the use of predicates and style control.

**【Example 1: Basic Attributes and Interaction (Holding, Touching, HasState)】**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["woman", "apple", "basket"],
  "style_control": {{
    "target_style": "oil painting"
  }},
  "target_dependency_depth": {{
    "num_object_class": 3,
    "regular": 3,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 1,
    "closure_depths": [3],
    "exists_forall_struct": [["exists", "exists", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["Holding", "HasState", "HasColor", "IsStyle"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "This is an oil painting style image. The scene features a woman holding a red apple. The apple is whole. The woman is also holding a basket.",
  "dsl_representation": "(and (IsStyle 'oil painting') (exists ?w (exists ?a (exists ?b (and (Is ?w 'woman') (Is ?a 'apple') (Is ?b 'basket') (HasColor ?a 'red') (HasState ?a 'whole') (Holding ?w ?a) (Holding ?w ?b))))))"
}}

**【Example 2: Spatial Containment and Material (In, On, HasMaterial, HasShape)】**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["table", "bowl", "spoon", "glass"],
  "style_control": {{
    "target_style": null
  }},
  "target_dependency_depth": {{
    "num_object_class": 4,
    "regular": 4,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 1,
    "closure_depths": [4],
    "exists_forall_struct": [["exists", "exists", "exists", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["On", "HasMaterial", "HasShape"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "A round bowl sits on a wooden table. Inside the bowl is a metal spoon. There is also a glass cup on the table.",
  "dsl_representation": "(exists ?t (exists ?b (exists ?s (exists ?g (and (Is ?t 'table') (HasMaterial ?t 'wooden') (Is ?b 'bowl') (HasShape ?b 'round') (Is ?s 'spoon') (HasMaterial ?s 'metal') (Is ?g 'glass') (On ?b ?t) (In ?s ?b) (On ?g ?t))))))"
}}

**【Example 3: Relative Position and Universal Quantifier (LeftOf, RightOf, forall)】**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["car", "bus", "tree"],
  "style_control": {{
    "target_style": "cyberpunk"
  }},
  "target_dependency_depth": {{
    "num_object_class": 3,
    "regular": 3,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 1,
    "closure_depths": [3],
    "exists_forall_struct": [["exists", "forall", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["LeftOf", "RightOf", "IsStyle"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "In this image, all directions are relative to the frame. Generate a cyberpunk style image. There is a tree on the left side of the frame. For all cars in the image, they are located to the right of this tree. Additionally, there is a bus located to the left of the tree.",
  "dsl_representation": "(and (IsStyle 'cyberpunk') (exists ?t (and (Is ?t 'tree') (forall ?c (implies (Is ?c 'car') (RightOf ?c ?t))) (exists ?b (and (Is ?b 'bus') (LeftOf ?b ?t))))))"
}}

**【Example 4: Vertical Relations and Adjacency (Above, Below, NextTo)】**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["lamp", "desk", "chair", "rug"],
  "style_control": {{
    "target_style": "cartoon"
  }},
  "target_dependency_depth": {{
    "num_object_class": 4,
    "regular": 4,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 1,
    "closure_depths": [4],
    "exists_forall_struct": [["exists", "exists", "exists", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["Above", "NextTo", "IsStyle"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "In this image, all directions are relative to the frame. This is a cartoon style scene. A lamp hangs above a desk. Next to the desk is a chair. A rug is located below both the chair and the desk.",
  "dsl_representation": "(and (IsStyle 'cartoon') (exists ?l (exists ?d (exists ?c (exists ?r (and (Is ?l 'lamp') (Is ?d 'desk') (Is ?c 'chair') (Is ?r 'rug') (Above ?l ?d) (NextTo ?c ?d) (Below ?r ?c) (Below ?r ?d)))))))"
}}

**【Example 5: Multiple Closures and Negative Logic (not, HasState)】**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["door", "cat", "sofa"],
  "style_control": {{
    "target_style": null
  }},
  "target_dependency_depth": {{
    "num_object_class": 3,
    "regular": 2,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 2,
    "closure_depths": [1, 2],
    "exists_forall_struct": [["exists"], ["exists", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["HasState", "not", "On"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "There is a door that is closed. Furthermore, there is a cat that is not on the sofa.",
  "dsl_representation": "(and (exists ?d (and (Is ?d 'door') (HasState ?d 'closed'))) (exists ?c (exists ?s (and (Is ?c 'cat') (Is ?s 'sofa') (not (On ?c ?s))))))"
}}

---
#### Your Task

Now, please generate a **brand new**, **logical** scene description data pair strictly following the JSON format and the parameters specified below.
Please pay special attention to:
1.  **Style Handling**: If `style_control.target_style` is `null`, do not generate the `(IsStyle ...)` predicate, and do not mention style in the natural language description. Otherwise, it must be included.
2.  **Predicate Constraints**: You can only use predicates existing in the DSL definition, and must prioritize using predicates specified in `required_predicates`. If using only `required_predicates` cannot generate a natural sample, you may appropriately add suitable predicates.
3.  **Vocabulary Constraints**: You can only use object types existing in the DSL definition, and must prioritize using vocabulary specified in `contained_vocabulary`. If a predicate like `Holding` exists, but `contained_vocabulary` does not contain an entity capable of this action (e.g., only containing inanimate objects), you may add an entity yourself.
4.  **Spatial Relation Annotation**: If your generated scene involves any spatial relationship predicates (e.g., LeftOf, RightOf, Above, Below, On, In, NextTo), you must insert the sentence "In this image, all directions are relative to the frame." to the start of the natural_language_description to provide clear context.

**Important**
In summary, the highest guideline for data generation is to ensure the generated data is reasonable, natural, and free of unnatural descriptions.

*   **Generation Parameters:**
{instruction}

*   **Output:**
{{
  "natural_language_description": "...",
  "dsl_representation": "..."
}}

Please directly output a complete, comment-free JSON object, and do not include any additional explanation or Markdown code block markers.
"""

prompt_style = ""

prompt_style_diffusion = ""

prompts_eval = """You are a top-tier multimodal AI analyst proficient in First-Order Logic and image content verification.

**Task:**
Your task is to precisely analyze a given image and perform a dual verification based on a "Natural Language Constraint" and a structured "Logical Expression". You need to complete two core tasks:
1.  **Overall Constraint Evaluation (Hard Constraint):** Determine if the image content **completely** satisfies the overall requirements of the "Natural Language Constraint".
2.  **Atomic Clause Verification (Soft Constraint):** Analyze every **atomic clause** in the "Logical Expression" one by one, and filter out the clauses that hold true in the image.

---
#### **Input Format Description**
The "Logical Expression" you receive has a specific structure:
1.  **Independent Logical Blocks:** The entire expression consists of one or more "blocks" that are logically independent of each other. These blocks are connected at the top level by `and`.
2.  **Quasi-CNF (Quasi-Conjunctive Normal Form):** Inside each regular "logical block" is a quasi-CNF form: quantifiers (`forall`, `exists`) are placed at the beginning, followed by a series of **atomic clauses** connected by `and`.
3.  **Atomic Clauses:** These are the smallest units for your "soft constraint" verification. It is typically a simple predicate call (e.g., `(Is ?x 'cat')`) or a disjunction `(or ...)`.

---
#### **Analysis Instructions**
0.  **The "Zero-Evidence" Protocol (CRITICAL PRIORITY):**
    *   **Image Integrity Check:** Before analyzing logic, scan the image globally.
    *   **Immediate Fail Condition:** If the image is **solid black, solid white, random noise, severe blur, or completely dark** with no discernible objects, you MUST STOP processing immediately.
    *   **Outcome:** In this case, `satisfies_constraint` MUST be `false`, and `satisfied_clauses` MUST be strictly `[]` (empty list). Do not attempt to hallucinate objects.

1.  **Overall Constraint Evaluation (`satisfies_constraint`):**
    *   First, comprehensively understand the full requirements of the "Natural Language Constraint" and the "Logical Expression".
    *   Carefully observe the image to determine if it **flawlessly satisfies all requirements**. Specifically, colors, materials, states, styles, and spatial relations must be exactly consistent.
    *   If the semantics of the natural language are ambiguous, **you must use the strict definition of the "Logical Expression" as the final judgment standard**.
    *   If fully satisfied, it is `true`; if there is any discrepancy (e.g., incorrect material, reversed position), it is `false`.

2.  **Atomic Clause Verification (`satisfied_clauses`):**
    *   Traverse **all** **atomic clauses** in the "Logical Expression" (including those inside all independent logical blocks).
    *   Independently judge whether each atomic clause holds true in the image.
    *   Collect the complete strings of all **atomic clauses that hold true** in the image into a list.
    *   **Prohibition of "Vacuous Truth" for `forall`:**
        *   In standard logic, "All unicorns are pink" is True if there are no unicorns (Vacuous Truth).
        *   **IN THIS TASK, YOU MUST REJECT VACUOUS TRUTH.**
        *   A clause starting with `forall ?x` or involving a group check is considered "Satisfied" **ONLY IF** actual instances of `?x` exist in the image AND they meet the condition.
        *   **Rule:** If the subject of a `forall` clause (e.g., "all fruits") is absent from the image, that clause is **FALSE**. Do not include it in the output.
  

**Special Case:** If the image content is completely unrelated to the scene described in the "Natural Language Constraint", `satisfies_constraint` should be `false`, and `satisfied_clauses` should be an empty list `[]`.

---
#### **Example 1**

Suppose the input is as follows:

*   **Image:** An image showing a red apple on a wooden table.
*   **Natural Language Constraint:** "A red apple is on a metal table."
*   **Logical Expression:**
(exists ?t 
  (exists ?a 
    (and 
      (Is ?t 'table')
      (Is ?a 'apple')
      (On ?a ?t)
      (HasColor ?a 'red')
      (HasMaterial ?t 'metal')
    )
  )
)

**Your analysis process should be:**
1.  **Overall Evaluation:** The natural language requires the table to be "metal", but the table in the image is "wooden". Therefore, the overall constraint is **not satisfied**. `satisfies_constraint` is `false`.
2.  **Clause Verification:**
    *   Atomic Clause 1: `(Is ?t 'table')` -> Holds, there is indeed a table in the image.
    *   Atomic Clause 2: `(Is ?a 'apple')` -> Holds, there is indeed an apple in the image.
    *   Atomic Clause 3: `(On ?a ?t)` -> Holds, the apple is indeed on the table.
    *   Atomic Clause 4: `(HasColor ?a 'red')` -> Holds, the apple is red.
    *   Atomic Clause 5: `(HasMaterial ?t 'metal')` -> **Does not hold**, the table in the image looks like wood, not metal.
3.  **Final Output:** Collect all valid atomic clauses.

**The corresponding JSON output should be:**
```json
{{
  "satisfies_constraint": false,
  "satisfied_clauses": [
    "(Is ?t 'table')",
    "(Is ?a 'apple')",
    "(On ?a ?t)",
    "(HasColor ?a 'red')"
  ]
}}
```

---
#### **Example 2 (The "Black Screen" & Vacuous Truth Case)**

*   **Image:** A completely black image (or an image with only static noise).
*   **Natural Language Constraint:** "All elephants in the room are pink and standing next to an apple."
*   **Logical Expression:**
(forall ?e
  (implies 
    (Is ?e 'elephant')
    (and 
      (HasColor ?e 'pink')
      (exists ?a (and (Is ?s 'apple') (NextTo ?e ?a)))
    )
  )
)

**Your analysis process should be:**
1.  **Step 0 Check:** The image is black. There is no visual content.
2.  **Constraint Check:** Since nothing is visible, the complex description of elephants and spaceships is definitely not satisfied. `satisfies_constraint` is `false`.
3.  **Clause Verification (Anti-Hallucination):**
    *   Logic says `forall` is True if no elephants exist (Vacuous Truth).
    *   **HOWEVER**, applying the **"Prohibition of Vacuous Truth"**: Since no elephant `?e` is visible in the pixels, the logic verification fails.
    *   No objects can be confirmed.
4.  **Final Output:** Return failure and an empty list.

**The corresponding JSON output should be:**
```json
{{
  "satisfies_constraint": false,
  "satisfied_clauses": []
}}
```

---
**Input:**

Natural Language Constraint:
{nl}

Logical Expression:
{cnf}

**Output Requirement:**
Please return your analysis result strictly in the following JSON format, **without adding any extra explanation, code markers, or explanatory text.**

```json
{{
  "satisfies_constraint": <true_or_false>,
  "satisfied_clauses": [
    "<Full string of the first satisfied atomic clause>",
    "<Full string of the second satisfied atomic clause>",
    "..."
  ]
}}
```
"""

prompt_check = """You are an extremely rigorous First-Order Logic analyst and visual scene data quality verification expert. Your task is to review a data pair consisting of a Natural Language description (NL) and a Domain Specific Language (DSL) to ensure its logical soundness and the consistency between the two. Your input and output must be in strict JSON format.

#### DSL Domain Definition
You must strictly adhere to the complete syntax and vocabulary of the following DSL for judgment, including objects, attributes, states, styles, and spatial relations.
{dsl}

#### Core Review Principles

Your review process consists of two core steps, which must be executed in order:

**1. Contradiction Check:**
First, you must determine if the DSL expression itself contains intrinsic contradictions that make it **unsatisfiable** in the physical world or image logic. Mainly check for two types of contradictions:
*   **Physical/Geometric Paradoxes:**
    *   **Cyclic Containment/Support:** E.g., `(In ?a ?b)` and `(In ?b ?a)`, or `(On ?a ?b)` and `(On ?b ?a)`.
    *   **Positional Conflicts:** Requiring `(LeftOf ?a ?b)` and `(RightOf ?a ?b)` simultaneously.
    *   **State Conflicts:** The same variable holding mutually exclusive states or attributes simultaneously, e.g., `(HasState ?a 'open')` and `(HasState ?a 'closed')`.
*   **Logical Paradoxes:** Constraints caused by using `forall` quantifiers leading to infinite recursion or impossibilities within a finite frame (e.g., "Everyone has another person to their left").

If any such contradiction is detected, your task ends immediately, and `is_contradictory` is set to `true`.

**2. Alignment Check:**
You only need to perform this check if the DSL has **no** intrinsic contradictions. The core principle is: **The DSL expression must not introduce any logical, attribute, or spatial constraints not explicitly stated or strongly implied in the NL.**

*   **Style Consistency (Style Check):** If the DSL contains the `(IsStyle '...')` predicate, the NL **must** explicitly mention that style (e.g., "oil painting", "cyberpunk"). If the NL does not mention style but the DSL defines it, it is considered **misaligned**.
*   **Attribute/Relation Hallucination (Hallucination Check):**
    *   NL: "There is an apple on the table."
    *   DSL: `(exists ?t ?a (and ... (HasColor ?a 'red') ...))` -> **Misaligned** (NL didn't say it was red).
    *   DSL: `(exists ?t ?a (and ... (On ?a ?t) ...))` -> **Aligned** (NL implies 'On').
*   **Layout Over-specification:** If the NL only says "There are A and B", but the DSL forcibly prescribes `(LeftOf ?a ?b)`, it is considered **misaligned**.

#### Output Format
You must return a strict JSON object containing the following three fields:
*   `"is_contradictory"` (boolean): `true` if the DSL has intrinsic contradictions, otherwise `false`.
*   `"is_aligned"` (boolean | null):
    *   If `"is_contradictory"` is `true`, this field must be `null`.
    *   If the DSL has no contradictions, determine if the NL and DSL are aligned. `true` for aligned, `false` for misaligned.
*   `"corrected_nl_description"` (string | null):
    *   If `"is_aligned"` is `true` or `"is_contradictory"` is `true`, this field must be `null`.
    *   Only when `"is_aligned"` is `false`, this field needs to contain a **corrected, clear, and unambiguous natural language description strictly corresponding to the given DSL**. The corrected description must cover all constraints in the DSL (including style, attributes, positions).

---
#### Few-shot Review Examples

**【Example 1: Physical/Geometric Paradox (Cyclic Containment)】**
*   **Input:**
{{
  "natural_language_description": "There is a ball in a box, and the box is inside that ball.",
  "dsl_representation": "(exists ?box (exists ?ball (and (Is ?box 'box') (Is ?ball 'ball') (In ?ball ?box) (In ?box ?ball))))"
}}
*   **Output:**
{{
  "is_contradictory": true,
  "is_aligned": null,
  "corrected_nl_description": null
}}

**【Example 2: Logical Paradox (Infinite Recursion)】**
*   **Input:**
{{
  "natural_language_description": "For every tree in the picture, there is necessarily another tree to its right.",
  "dsl_representation": "(forall ?t1 (implies (Is ?t1 'tree') (exists ?t2 (and (Is ?t2 'tree') (RightOf ?t2 ?t1)))))"
}}
*   **Output:**
{{
  "is_contradictory": true,
  "is_aligned": null,
  "corrected_nl_description": null
}}

**【Example 3: Misaligned (Style Hallucination)】**
*   **Input:**
{{
    "natural_language_description": "A cat is sleeping on the sofa.",
    "dsl_representation": "(and (IsStyle 'oil painting') (exists ?c (exists ?s (and (Is ?c 'cat') (Is ?s 'sofa') (On ?c ?s) (HasState ?c 'closed')))))"
}}
*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": false,
  "corrected_nl_description": "This is an oil painting. A cat in a closed state (likely referring to eyes closed) is on the sofa."
}}

**【Example 4: Misaligned (Space Relation Over-specification)】**
*   **Input:**
{{
    "natural_language_description": "There is a man and a cat in the picture.",
    "dsl_representation": "(exists ?m (exists ?c (and (Is ?m 'man') (Is ?c 'cat') (Holding ?m ?c))))"
}}
*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": false,
  "corrected_nl_description": "The picture shows a man holding a cat."
}}

**【Example 5: Qualified Sample】**
*   **Input:**
{{
  "natural_language_description": "Generate a cyberpunk style image. A red apple is placed on a metal table, with a knife next to it.",
  "dsl_representation": "(and (IsStyle 'cyberpunk') (exists ?a (exists ?t (exists ?k (and (Is ?a 'apple') (HasColor ?a 'red') (Is ?t 'table') (HasMaterial ?t 'metal') (Is ?k 'knife') (On ?a ?t) (NextTo ?k ?a))))))"
}}
*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": true,
  "corrected_nl_description": null
}}

---
#### Your Task

Now, please review the following data pair and strictly return your analysis result in the JSON format described above.

*   **Sample to Check:**
{sample_to_check}

*   **Output:**
{{
  "is_contradictory": ...,
  "is_aligned": ...,
  "corrected_nl_description": ...
}}
Please directly output a complete, comment-free JSON object, and do not include any additional explanation or Markdown code block markers.
"""

prompt_check_v3 = """You are a senior analyst proficient in First-Order Logic and visual arts design. Your task is to review and optimize data pairs of "Natural Language Description (NL)" and "Domain Specific Language (DSL)".

#### DSL Domain Definition
{dsl}

#### Core Review Principles

**1. Logic and Rationality Judgment (`is_contradictory`):**
Set to `true` if the following occur (this will cause the sample to be resampled):
*   **Logical Paradoxes:** Cyclic containment `(In ?a ?b) and (In ?b ?a)`, cyclic support `(On ?a ?b) and (On ?b ?a)`, positional conflicts (same person on both left and right).
*   **Common Sense Fallacies (Priority):**
    *   **Misuse of States:** It is strictly forbidden to describe people, children, or animals as "whole". This is a typical machine translation error; humans assume living beings are whole by default. Other jarring misuses of states are also prohibited.
    *   **Extremely Unnatural Physical Combinations:** E.g., "shoes inside a cake", "a bus floating above an apple", "an elephant placed on a laptop". (Note: One-to-one pairings like "an apple under every tree" are allowed and are not considered fallacies).

**2. Alignment and Naturalization Polishing (`is_aligned` & `corrected_nl_description`):**
Even if the logic is fine, if the NL expression is unnatural, set `is_aligned: false` and provide a polished version in `corrected_nl_description`.
*   **Eliminate Redundant Logic:** Strictly forbid repetitive descriptions like "A is above B, which means B is below A".
*   **Remove "Machine Flavor":** Do not translate as "For all...", use natural language like "All trees..." or "Every tree...".
*   **Attribute Integration:** Colors, materials, and states in the DSL (e.g., `on`, `broken`, `smiling`) must be naturally integrated into the description.
*   **Translation Style:** Must conform to human expression habits, similar to high-quality prompts for Midjourney or DALL-E.

#### Output Format
You must return a strict JSON object:
{{
  "is_contradictory": boolean,
  "is_aligned": boolean,
  "corrected_nl_description": string | null
}}
*Note: If `is_contradictory` is true, set the latter two fields to false and null respectively.*

---
#### Review Examples

**【Example 1: Physical Fallacy (Cyclic Support)】**
*   **Input:**
{{
  "natural_language_description": "The book is on the table, and the table is on the book.",
  "dsl": "(and (On ?book ?table) (On ?table ?book))"
}}

*   **Output:**
{{
  "is_contradictory": true,
  "is_aligned": false,
  "corrected_nl_description": null
}}

**【Example 2: Unreasonable Content (Whole Person)】**
*   **Input:**
{{
  "natural_language_description": "A whole child is running.",
  "dsl": "(and (Is ?c 'child') (HasState ?c 'whole') (HasState ?c 'running'))"
}}

*   **Output:**
{{
  "is_contradictory": true,
  "is_aligned": false,
  "corrected_nl_description": null
}}

**【Example 3: Unnatural/Redundant (Needs Polishing)】**
*   **Input:**
{{
  "natural_language_description": "There is a red apple on a wooden table. That is to say, the table is under the red apple.",
  "dsl": "(exists ?a ?t (and (Is ?a 'apple') (HasColor ?a 'red') (Is ?t 'table') (HasMaterial ?t 'wooden') (On ?a ?t)))"
}}

*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": false,
  "corrected_nl_description": "There is a wooden table in the scene with a red apple placed on it."
}}

**【Example 4: 1-to-1 Pairing (Reasonable, Only Polish)】**
*   **Input:**
{{
  "natural_language_description": "For every bird, there is a laptop to its right.",
  "dsl": "(forall ?b (implies (Is ?b 'bird') (exists ?l (and (Is ?l 'laptop') (RightOf ?l ?b)))))"
}}

*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": false,
  "corrected_nl_description": "To the right of every bird in the scene, there is a laptop."
}}

**【Example 5: Perfect Sample】**
*   **Input:**
{{
  "natural_language_description": "An oil painting style image. A broken ceramic cup sits on a rug.",
  "dsl": "(and (IsStyle 'oil painting') (exists ?c ?r (and (Is ?c 'cup') (HasMaterial ?c 'ceramic') (HasState ?c 'broken') (Is ?r 'rug') (On ?c ?r))))"
}}

*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": true,
  "corrected_nl_description": null
}}

---
#### Your Task
Please review the following data:
*   **Input:**
{sample_to_check}

*   **Output:**
{{
  "is_contradictory": ...,
  "is_aligned": ...,
  "corrected_nl_description": ...
}}

Please directly output a complete, comment-free JSON object, and do not include any additional explanation or Markdown code block markers.
"""

prompt_check_v7 = """You are a senior analyst proficient in First-Order Logic and visual arts design. Your task is to review and optimize data pairs of "Natural Language Description (NL)" and "Domain Specific Language (DSL)".

#### DSL Domain Definition
{dsl}

#### Core Review Principles (STRICT ENFORCEMENT)

**1. Critical Logic & Physics Failures (`is_contradictory` = true):**
Set `is_contradictory: true` (Resample) ONLY if the following occur:

*   **A. Attribute-Object Mismatch (The "Rectangular Lion" Rule):**
    *   **Geometric Hallucinations:** Living beings (lions, people) and complex mechanisms (bicycles, cars) CANNOT be described with simple geometric primitives unless the style is explicitly "Abstract" or "Cubist".
        *   *REJECT:* "A rectangular lion", "A triangular bicycle", "A square horse", "An oval car".
        *   *ACCEPT:* "A rectangular table", "A round ball", "A triangular sandwich".
    *   **Material Absurdity:**
        *   *REJECT:* "A water chair", "A cloud made of iron" (unless surrealism is specified).

*   **B. Scale & Mass Absurdity (The "Holding" Rule):**
    *   **Allowed (Quantity):** A person/animal CAN hold multiple portable items (e.g., "holding every basket", "holding all the apples", "holding a chair"). Do not reject based on quantity alone.
    *   **Forbidden (Mass/Immovability):** A person/animal CANNOT hold **Immovable or Massive** objects.
        *   *REJECT:* "A person holding a refrigerator", "A child holding a house", "A man holding a bus", "A woman holding a bed", "A person holding a tree".

*   **C. Impossible Containment (The "Inside" Rule):**
    *   **Solid Objects:** Items cannot be `Inside` solid organic/inorganic objects.
        *   *REJECT:* "A key inside an apple", "A laptop inside a horse", "A book inside a solid rock".
    *   **Size Constraints:** A large object cannot be inside a significantly smaller one.
        *   *REJECT:* "A bicycle inside a basket", "A sofa inside a backpack".

*   **D. Logical Paradoxes:**
    *   Cyclic dependency `(In ?a ?b) and (In ?b ?a)`, or `(LeftOf ?a ?b) and (RightOf ?a ?b)`.

**2. Alignment and Naturalization Polishing (`is_aligned` & `corrected_nl_description`):**
Even if the logic is fine, if the NL expression is unnatural, set `is_aligned: false` and provide a polished version.

*   **Eliminate Redundant Logic:** Strictly forbid repetitive descriptions like "A is above B, which means B is below A". Keep it concise.
*   **Remove "Machine Flavor":**
    *   **Strictly Forbidden:** Describing living beings/objects as "whole" (e.g., "A whole child", "A whole cat"). This is a translation error.
    *   **Phrasing:** Do not translate logic quantifiers literally. Avoid "For all x...", use natural language like "All trees..." or "Every tree...".
*   **Attribute Integration:** Colors, materials, and states in the DSL (e.g., `on`, `broken`, `smiling`) must be naturally integrated into the noun phrase rather than listed separately.
    *   *Bad:* "There is a car. The car is red." -> *Good:* "A red car."
*   **Translation Style:** Must conform to human expression habits, similar to high-quality prompts for Midjourney or DALL-E (Visual, Descriptive, Fluent).
*   **Important:** If the original description contains the sentence "In this image, all directions are relative to the frame.", you must preserve it verbatim.

#### Output Format
You must return a strict JSON object:
{{
  "is_contradictory": boolean,
  "is_aligned": boolean,
  "corrected_nl_description": string | null
}}
*Note: If `is_contradictory` is true, set the latter two fields to false and null respectively.*

---
#### Review Examples

**【Case 1: Geometric Hallucination (Refuse)】**
*   **Input:** "A cyberpunk style scene where every lion is rectangular."
*   **Analysis:** Lions cannot be rectangular. Attribute error.
*   **Output:** {{ "is_contradictory": true, "is_aligned": false, "corrected_nl_description": null }}

**【Case 2: Mass/Scale Violation (Refuse)】**
*   **Input:** "A child is holding a refrigerator."
*   **Analysis:** A refrigerator is too heavy for a child.
*   **Output:** {{ "is_contradictory": true, "is_aligned": false, "corrected_nl_description": null }}

**【Case 3: Unnatural/Redundant (Polish)】**
*   **Input:** "There is a red apple on a wooden table. That is to say, the table is under the red apple."
*   **Analysis:** Logic is valid, but the second sentence is redundant.
*   **Output:** {{ "is_contradictory": false, "is_aligned": false, "corrected_nl_description": "A wooden table with a red apple placed on it." }}

**【Case 4: Machine Flavor/Attribute Integration (Polish)】**
*   **Input:** "For every bird, there is a laptop. The laptop is broken."
*   **Analysis:** "For every" is too logical. "The laptop is broken" should be integrated.
*   **Output:** {{ "is_contradictory": false, "is_aligned": false, "corrected_nl_description": "Next to every bird sits a broken laptop." }}

**【Case 5: Valid "Greedy" Quantifier (Accept)】**
*   **Input:** "A woman is holding every basket in the scene."
*   **Analysis:** Baskets are portable. Holding multiple is physically possible.
*   **Output:** {{ "is_contradictory": false, "is_aligned": true, "corrected_nl_description": null }}

---
#### Your Task
Please review the following data:
*   **Input:**
{sample_to_check}

*   **Output:**
{{
  "is_contradictory": ...,
  "is_aligned": ...,
  "corrected_nl_description": ...
}}

Please directly output a complete, comment-free JSON object, and do not include any additional explanation or Markdown code block markers.
"""

prompt_check_v8 = """You are a senior analyst proficient in First-Order Logic and visual arts design. Your task is to review and optimize data pairs of "Natural Language Description (NL)" and "Domain Specific Language (DSL)".

#### DSL Domain Definition
{dsl}

#### Core Review Principles (STRICT ENFORCEMENT)

**1. Critical Logic & Physics Failures (`is_contradictory` = true):**
Set `is_contradictory: true` (Resample) ONLY if the following occur:

*   **A. Attribute-Object Mismatch (The "Rectangular Lion" Rule):**
    *   **Geometric Hallucinations:** Living beings (lions, people) and complex mechanisms (bicycles, cars) CANNOT be described with simple geometric primitives unless the style is explicitly "Abstract" or "Cubist".
        *   *REJECT:* "A rectangular lion", "A triangular bicycle", "A square horse", "An oval car".
        *   *ACCEPT:* "A rectangular table", "A round ball", "A triangular sandwich".
    *   **Material Absurdity:**
        *   *REJECT:* "A water chair", "A cloud made of iron" (unless surrealism is specified).

*   **B. Scale & Mass Absurdity (The "Holding" Rule):**
    *   **Allowed (Quantity):** A person/animal CAN hold multiple portable items (e.g., "holding every basket", "holding all the apples", "holding a chair"). Do not reject based on quantity alone.
    *   **Forbidden (Mass/Immovability):** A person/animal CANNOT hold **Immovable or Massive** objects.
        *   *REJECT:* "A person holding a refrigerator", "A child holding a house", "A man holding a bus", "A woman holding a bed", "A person holding a tree".

*   **C. Impossible Containment (The "Inside" Rule):**
    *   **Solid Objects:** Items cannot be `Inside` solid organic/inorganic objects.
        *   *REJECT:* "A key inside an apple", "A laptop inside a horse", "A book inside a solid rock".
    *   **Size Constraints:** A large object cannot be inside a significantly smaller one.
        *   *REJECT:* "A bicycle inside a basket", "A sofa inside a backpack".

*   **D. Logical Paradoxes:**
    *   Cyclic dependency `(In ?a ?b) and (In ?b ?a)`, or `(LeftOf ?a ?b) and (RightOf ?a ?b)`.

**2. Alignment and Naturalization Polishing (`is_aligned` & `corrected_nl_description`):**
Even if the logic is fine, if the NL expression is unnatural or logically misaligned, set `is_aligned: false` and provide a polished version.

*   **Preserve Logical Scope (Quantifier Order):** Do not alter the logical meaning by changing the scope of quantifiers (`forall`, `exists`). This is a critical translation error, not a stylistic choice.
    *   *DSL Logic:* `forall X, exists Y` means "For each X, there is a Y". This allows for a *different* Y for each X.
    *   *Incorrect NL Translation:* "A Y is [relation] to every X". This incorrectly implies `exists Y, forall X` (a single Y for all X's).
    *   *Correct NL Translation:* "Every X has a Y [relation] to it." or "For each X, there is a Y...".

*   **Eliminate Redundant Logic:** Strictly forbid repetitive descriptions like "A is above B, which means B is below A". Keep it concise.

*   **Remove "Machine Flavor":**
    *   **Strictly Forbidden:** Describing living beings/objects as "whole" (e.g., "A whole child", "A whole cat"). This is a translation error.
    *   **Phrasing:** Do not translate logic quantifiers literally (e.g., "For all x..."), but ensure their logical scope is preserved as per the rule above. Use natural phrasing like "All trees..." or "Every tree...".

*   **Attribute Integration:** Colors, materials, and states in the DSL (e.g., `on`, `broken`, `smiling`) must be naturally integrated into the noun phrase rather than listed separately.
    *   *Bad:* "There is a car. The car is red." -> *Good:* "A red car."

*   **Translation Style:** Must conform to human expression habits, similar to high-quality prompts for Midjourney or DALL-E (Visual, Descriptive, Fluent).

*   **Important:** If the original description contains the sentence "In this image, all directions are relative to the frame.", you must preserve it verbatim.

#### Output Format
You must return a strict JSON object:
{{
  "is_contradictory": boolean,
  "is_aligned": boolean,
  "corrected_nl_description": string | null
}}
*Note: If `is_contradictory` is true, set the latter two fields to false and null respectively.*

---
#### Review Examples

**【Case 1: Geometric Hallucination (Refuse)】**
*   **Input:** "A cyberpunk style scene where every lion is rectangular."
*   **Analysis:** Lions cannot be rectangular. Attribute error.
*   **Output:** {{ "is_contradictory": true, "is_aligned": false, "corrected_nl_description": null }}

**【Case 2: Mass/Scale Violation (Refuse)】**
*   **Input:** "A child is holding a refrigerator."
*   **Analysis:** A refrigerator is too heavy for a child.
*   **Output:** {{ "is_contradictory": true, "is_aligned": false, "corrected_nl_description": null }}

**【Case 3: Unnatural/Redundant (Polish)】**
*   **Input:** "There is a red apple on a wooden table. That is to say, the table is under the red apple."
*   **Analysis:** Logic is valid, but the second sentence is redundant.
*   - **Output:** {{ "is_contradictory": false, "is_aligned": false, "corrected_nl_description": "A wooden table with a red apple placed on it." }}

**【Case 4: Machine Flavor/Attribute Integration (Polish)】**
*   **Input:** "For every bird, there is a laptop. The laptop is broken."
*   **Analysis:** "For every" is acceptable but can be more natural. "The laptop is broken" should be integrated.
*   **Output:** {{ "is_contradictory": false, "is_aligned": false, "corrected_nl_description": "Next to every bird sits a broken laptop." }}

**【Case 5: Quantifier Scope Misalignment (Polish)】**
*   **Input (DSL Context):** `(forall ?p (plant ?p) (exists ?m (man ?m) (LeftOf ?m ?p)))`
*   **Input (NL):** "A man is to the left of every plant."
*   **Analysis:** The NL incorrectly implies a *single man* for all plants (`exists man, forall plant`). The DSL's `forall plant, exists man` scope allows for a different man for each plant. This is a logical scope misalignment.
*   **Output:** {{ "is_contradictory": false, "is_aligned": false, "corrected_nl_description": "Every plant has a man to its left." }}

**【Case 6: Valid "Greedy" Quantifier (Accept)】**
*   **Input:** "A woman is holding every basket in the scene."
*   **Analysis:** Baskets are portable. Holding multiple is physically possible. The NL structure correctly implies `exists woman, forall basket`, which is a valid logical statement.
*   **Output:** {{ "is_contradictory": false, "is_aligned": true, "corrected_nl_description": null }}

---
#### Your Task
Please review the following data:
*   **Input:**
{sample_to_check}

*   **Output:**
{{
  "is_contradictory": ...,
  "is_aligned": ...,
  "corrected_nl_description": ...
}}

Please directly output a complete, comment-free JSON object, and do not include any additional explanation or Markdown code block markers.
"""

prompt_filter = """You are an expert data quality analyst. Your task is to evaluate the quality of a data sample, which consists of a `natural_language_description` and a `dsl_representation`. You must determine if the sample is "qualified" based on a strict set of rules.

**A qualified sample must meet both of these criteria:**
1.  **Perfect Alignment:** The `dsl_representation` must be a perfect and accurate logical translation of the `natural_language_description`. All objects, attributes (color, material, state, shape), relationships (spatial, possessive), and quantifiers (`a`, `every`, `all`) must match exactly.
2.  **Logical Coherence:** The `natural_language_description` itself must be logical, reasonable, and free of internal contradictions.

**A sample is unqualified if it has any of the following issues:**
*   **Misalignment:** The DSL does not match the text. This includes errors in relations, attributes, object existence, or quantifiers.
*   **Hallucination:** The DSL introduces objects, attributes, or relationships that are not mentioned at all in the text.
*   **Quantifier Errors:** These are critical failures.
    *   **Existential vs. Universal Mismatch:** The text describes a single object (e.g., "a green shirt"), but the DSL uses a universal quantifier (`forall`) to make a claim about *all* such objects in the scene.
    *   **Incorrect Scope:** The text applies a condition to a subset (e.g., "Every *empty* bottle..."), but the DSL incorrectly applies it more broadly (e.g., "For *every* bottle... it is empty...").
    *   **Scope Inversion (`exists/forall`):** The text implies `exists X such that forall Y...` (one X is related to all Ys), but the DSL incorrectly states `forall Y, exists X...` (for each Y, there might be a different X).

Your response **MUST** be a JSON object with a single key, `is_qualified`, and a boolean value (`true` for qualified, `false` for unqualified). Do not include any explanations or any other text in your output.

---
### **Few-shot Examples**

**Example 1: Qualified Sample (Correct Alignment)**

**Input:**
{{
  "natural_language_description": "In this image, all directions are relative to the frame. A cartoon style scene features a red sofa with a teddy bear and a sitting lion holding a metal hammer. To the left of the sofa is a basket containing every bottle, while to the right, a dog sleeps on a wooden chair.",
  "dsl_representation": "(and (IsStyle 'cartoon') (exists ?s (exists ?l (exists ?h (exists ?b (and (Is ?s 'sofa') (HasColor ?s 'red') (Is ?l 'lion') (HasState ?l 'sitting') (On ?l ?s) (Is ?h 'hammer') (HasMaterial ?h 'metal') (Holding ?l ?h) (Is ?b 'basket') (LeftOf ?b ?s) (forall ?bt (implies (Is ?bt 'bottle') (In ?bt ?b))) (exists ?tb (exists ?c (exists ?d (and (Is ?tb 'teddy bear') (On ?tb ?s) (Is ?c 'chair') (HasMaterial ?c 'wooden') (RightOf ?c ?s) (Is ?d 'dog') (HasState ?d 'sleeping') (On ?d ?c)))))))))))"
}}

**Output:**
{{
  "is_qualified": true
}}

---

**Example 2: Unqualified Sample (Existential vs. Universal Quantifier Mismatch)**
*Reason for being unqualified: The text describes 'a green shirt' worn by one specific child, but the DSL incorrectly uses `forall` to claim that 'every shirt' in the scene is green and worn by that child.*

**Input:**
{{
  "natural_language_description": "In this image, all directions are relative to the frame. A cartoon-style scene features a child wearing a green shirt sitting on a chair and holding a fork.",
  "dsl_representation": "(and (IsStyle 'cartoon') (exists ?c (exists ?ch (exists ?l (exists ?hp (exists ?p (and (Is ?c 'child') (Is ?ch 'chair') (Is ?l 'laptop') (Is ?hp 'headphones') (Is ?p 'pizza') (On ?c ?ch) (NextTo ?l ?ch) (NextTo ?hp ?l) (LeftOf ?p ?l) (HasShape ?p 'round') (forall ?s (implies (Is ?s 'shirt') (and (HasColor ?s 'green') (On ?s ?c)))) (exists ?f (exists ?sa (and (Is ?f 'fork') (Is ?sa 'sandwich') (Holding ?c ?f) (On ?sa ?p)))))))))))"
}}

**Output:**
{{
  "is_qualified": false
}}

---

**Example 3: Unqualified Sample (Incorrect Quantifier Scope)**
*Reason for being unqualified: The text specifies 'Every empty bottle', applying the condition 'empty' before the universal claim. The DSL incorrectly makes a claim about 'every bottle' and then asserts it is 'empty' inside the quantifier's scope, which is a different logical statement.*

**Input:**
{{
  "natural_language_description": "In this image, all directions are relative to the frame. The scene is rendered in pixel art style. Every empty bottle is placed inside a basket sitting on a bench.",
  "dsl_representation": "(and (IsStyle 'pixel art') (forall ?bt (implies (Is ?bt 'bottle') (exists ?bs (exists ?d (exists ?l (exists ?w (exists ?u (exists ?bn (exists ?bk (and (Is ?bs 'bookshelf') (HasMaterial ?bs 'wooden') (Is ?d 'desk') (RightOf ?bs ?d) (Is ?l 'laptop') (HasState ?l 'open') (On ?l ?d) (Is ?w 'woman') (Is ?u 'umbrella') (HasColor ?u 'red') (Holding ?w ?u) (Is ?bn 'bench') (LeftOf ?d ?bn) (NextTo ?w ?bn) (Is ?bk 'basket') (On ?bk ?bn) (HasState ?bt 'empty') (In ?bt ?bk))))))))))))"
}}

**Output:**
{{
  "is_qualified": false
}}

---

**Example 4: Unqualified Sample (Hallucinated Object and Relation)**
*Reason for being unqualified: The DSL includes a complex statement about 'all buses' (`forall ?bg (implies (Is ?bg 'bus')...)`), but the natural language description does not mention a bus at all.*

**Input:**
{{
  "natural_language_description": "In this image, all directions are relative to the frame. This cartoon-style scene features a man wearing a jacket. To his right stands a wooden table supporting a plant and a plate with a metal fork inside. A cat is next to the plant, and a blue butterfly hovers above the cat.",
  "dsl_representation": "(and (IsStyle 'cartoon') (exists ?m (exists ?j (exists ?t (exists ?p (and (Is ?m 'man') (Is ?j 'jacket') (On ?j ?m) (Is ?t 'table') (HasMaterial ?t 'wooden') (RightOf ?t ?m) (Is ?p 'plate') (On ?p ?t) (forall ?bg (implies (Is ?bg 'bus') (RightOf ?bg ?t))) (exists ?f (exists ?pl (exists ?c (exists ?bt (exists ?bi (and (Is ?f 'fork') (HasMaterial ?f 'metal') (In ?f ?p) (Is ?pl 'plant') (On ?pl ?t) (Is ?c 'cat') (NextTo ?c ?pl) (Is ?bt 'butterfly') (HasColor ?bt 'blue') (Above ?bt ?c) (Is ?bi 'bus') (RightOf ?bi ?t)))))))))))))"
}}

**Output:**
{{
  "is_qualified": false
}}
---

**Example 5: Unqualified Sample (Quantifier Scope Inversion - `exists/forall` Confusion)**
*Reason for being unqualified: The text describes 'a man' (singular, existential) who stands next to 'every chair' (universal). This implies one man is related to all chairs (`exists M forall C`). The DSL incorrectly uses `forall C, exists M...`, which allows for the possibility of a different man for each chair, misrepresenting the description's meaning.*

**Input:**
{{
  "natural_language_description": "In this image, all directions are relative to the frame. A cartoon-style scene where a man stands next to every chair, holding a knife and a pizza.",
  "dsl_representation": "(and (IsStyle 'cartoon') (forall ?c (implies (Is ?c 'chair') (exists ?m (exists ?k (exists ?p (exists ?s (exists ?b (exists ?h (exists ?cup (and (Is ?m 'man') (Is ?k 'knife') (Is ?p 'pizza') (Is ?s 'sofa') (Is ?b 'boat') (Is ?h 'hammer') (Is ?cup 'cup') (NextTo ?m ?c) (Holding ?m ?k) (Holding ?m ?p) (LeftOf ?s ?m) (NextTo ?b ?s) (On ?h ?s) (HasColor ?cup 'yellow') (LeftOf ?cup ?b))))))))))))"
}}
**Output:**
{{
  "is_qualified": false
}}
---

### **Sample to Evaluate**

**Input:**
{example}

**Output:**
{{
  "is_qualified": ...
}}

Please directly output a complete, comment-free JSON object, and do not include any additional explanation or Markdown code block markers.
"""
