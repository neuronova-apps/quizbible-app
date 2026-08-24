package com.neuronova.quizbible.data.model

import com.google.gson.annotations.SerializedName

enum class Testament {
    @SerializedName("OT") OT,
    @SerializedName("NT") NT
}

enum class Difficulty(val displayName: String) {
    @SerializedName("BASIC") BASIC("Básico"),
    @SerializedName("INTERMEDIATE") INTERMEDIATE("Intermedio"),
    @SerializedName("ADVANCED") ADVANCED("Avanzado"),
    @SerializedName("EXPERT") EXPERT("Experto")
}

enum class QuestionType {
    @SerializedName("MULTIPLE_CHOICE") MULTIPLE_CHOICE,
    @SerializedName("TRUE_FALSE") TRUE_FALSE
}

enum class AuditStatus {
    @SerializedName("VERIFIED") VERIFIED,
    @SerializedName("INCONCLUSIVE") INCONCLUSIVE,
    @SerializedName("REQUIRES_CORRECTION") REQUIRES_CORRECTION
}

data class QuizOption(
    val id: String,
    val text: String
)

data class QuizQuestion(
    val id: String,
    val testament: Testament,
    val book: String,
    val chapter: Int,
    val verseStart: Int,
    val verseEnd: Int? = null,
    val referenceDisplay: String,
    val category: String,
    val subcategory: String? = null,
    val characters: List<String> = emptyList(),
    val difficulty: Difficulty,
    val questionType: QuestionType,
    val prompt: String,
    val options: List<QuizOption>,
    val correctOptionId: String,
    val explanation: String,
    val eligibleModes: List<String> = emptyList(),
    val verificationTranslation: String = "RVR1960",
    val auditStatus: AuditStatus = AuditStatus.VERIFIED,
    val humanReviewStatus: String = "PENDING"
)

data class QuizRuntime(
    val schemaVersion: String,
    val generatedAt: String,
    val totalQuestions: Int,
    val questions: List<QuizQuestion>
)

enum class GameMode(
    val id: String,
    val eligibleModeKey: String,
    val title: String,
    val description: String
) {
    ANTIGUO_TESTAMENTO(
        "AT",
        "AT",
        "Antiguo Testamento",
        "Génesis a Malaquías (39 libros, 2620 preguntas)"
    ),
    NUEVO_TESTAMENTO(
        "NT",
        "NT",
        "Nuevo Testamento",
        "Mateo a Apocalipsis (27 libros, 1227 preguntas)"
    ),
    AMBOS_TESTAMENTOS(
        "AMBOS",
        "AMBOS",
        "Toda la Biblia",
        "Los 66 libros de la Biblia Protestante (3847 preguntas)"
    ),
    PERSONAJES_AT(
        "PERSONAJES_AT",
        "PERSONAJES_AT",
        "Personajes del AT",
        "Líderes, profetas y reyes del Antiguo Testamento (1005 preguntas)"
    ),
    PERSONAJES_NT(
        "PERSONAJES_NT",
        "PERSONAJES_NT",
        "Personajes del NT",
        "Apóstoles, discípulos y figuras del Nuevo Testamento (343 preguntas)"
    ),
    PERSONAJES_AMBOS(
        "PERSONAJES_AMBOS",
        "PERSONAJES_AMBOS",
        "Personajes Bíblicos",
        "Grandes personajes de toda la Biblia (1348 preguntas)"
    ),
    VERDADERO_FALSO_NT(
        "VERDADERO_FALSO_NT",
        "VERDADERO_FALSO_NT",
        "Verdadero o Falso (NT)",
        "Preguntas de afirmación sobre el Nuevo Testamento (155 preguntas)"
    ),
    VERDADERO_FALSO_AMBOS(
        "VERDADERO_FALSO_AMBOS",
        "VERDADERO_FALSO_AMBOS",
        "Verdadero o Falso (Global)",
        "Modo rápido de dos opciones (155 preguntas)"
    ),
    JESUS_PALABRAS(
        "JESUS_PALABRAS",
        "JESUS_PALABRAS",
        "Palabras de Jesús",
        "Enseñanzas y sermones del Señor Jesucristo (144 preguntas)"
    ),
    JESUS_MILAGROS(
        "JESUS_MILAGROS",
        "JESUS_MILAGROS",
        "Milagros de Jesús",
        "Sanidades, señales y maravillas de los Evangelios (47 preguntas)"
    ),
    JESUS_PARABOLAS(
        "JESUS_PARABOLAS",
        "JESUS_PARABOLAS",
        "Parábolas de Jesús",
        "Las historias y parábolas del Reino de Dios (37 preguntas)"
    )
}

enum class DifficultyFilter(val displayName: String, val difficulty: Difficulty?) {
    ALL("Mixto / Todas", null),
    BASIC("Básico", Difficulty.BASIC),
    INTERMEDIATE("Intermedio", Difficulty.INTERMEDIATE),
    ADVANCED("Avanzado", Difficulty.ADVANCED),
    EXPERT("Experto", Difficulty.EXPERT)
}
