package com.neuronova.quizbible.data.local

import android.content.Context
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.neuronova.quizbible.data.model.AuditStatus
import com.neuronova.quizbible.data.model.QuestionType
import com.neuronova.quizbible.data.model.QuizQuestion
import com.neuronova.quizbible.data.model.QuizRuntime
import java.io.InputStream
import java.io.InputStreamReader

object QuizBibleRuntimeLoader {
    const val DEFAULT_ASSET_NAME = "quiz_bible_protestant_rvr1960_runtime_v1.json"
    const val EXPECTED_TOTAL_QUESTIONS = 3847

    private val gson: Gson by lazy {
        GsonBuilder().create()
    }

    fun loadFromAssets(context: Context, assetName: String = DEFAULT_ASSET_NAME): QuizRuntime {
        context.assets.open(assetName).use { inputStream ->
            return loadFromInputStream(inputStream)
        }
    }

    fun loadFromInputStream(inputStream: InputStream): QuizRuntime {
        val reader = InputStreamReader(inputStream, Charsets.UTF_8)
        val runtime = gson.fromJson(reader, QuizRuntime::class.java)
            ?: throw IllegalStateException("No se pudo deserializar el runtime JSON. Fail-closed.")

        validateRuntime(runtime)
        return runtime
    }

    fun validateRuntime(runtime: QuizRuntime) {
        if (runtime.schemaVersion != "quizbible-runtime-v1") {
            throw IllegalStateException("Versión de esquema inválida: '${runtime.schemaVersion}'. Fail-closed.")
        }
        if (runtime.totalQuestions != EXPECTED_TOTAL_QUESTIONS || runtime.questions.size != EXPECTED_TOTAL_QUESTIONS) {
            throw IllegalStateException(
                "Cantidad de preguntas incorrecta: totalQuestions=${runtime.totalQuestions}, listSize=${runtime.questions.size}. Esperadas: $EXPECTED_TOTAL_QUESTIONS. Fail-closed."
            )
        }

        val seenIds = mutableSetOf<String>()
        for (q in runtime.questions) {
            if (q.id.isBlank()) {
                throw IllegalStateException("Pregunta con ID vacío. Fail-closed.")
            }
            if (!seenIds.add(q.id)) {
                throw IllegalStateException("ID de pregunta duplicado detectado: '${q.id}'. Fail-closed.")
            }
            if (q.prompt.isBlank()) {
                throw IllegalStateException("Pregunta '${q.id}' con prompt vacío. Fail-closed.")
            }
            if (q.auditStatus == AuditStatus.REQUIRES_CORRECTION) {
                throw IllegalStateException("Pregunta '${q.id}' con estado REQUIRES_CORRECTION en runtime. Fail-closed.")
            }

            when (q.questionType) {
                QuestionType.MULTIPLE_CHOICE -> {
                    if (q.options.size != 4) {
                        throw IllegalStateException("Pregunta MC '${q.id}' debe tener exactamente 4 opciones. Fail-closed.")
                    }
                    val optIds = q.options.map { it.id }.toSet()
                    if (optIds != setOf("A", "B", "C", "D")) {
                        throw IllegalStateException("Opciones de pregunta MC '${q.id}' deben ser A, B, C, D. Fail-closed.")
                    }
                    if (q.correctOptionId !in setOf("A", "B", "C", "D")) {
                        throw IllegalStateException("correctOptionId inválido '${q.correctOptionId}' en '${q.id}'. Fail-closed.")
                    }
                }
                QuestionType.TRUE_FALSE -> {
                    if (q.options.size != 2) {
                        throw IllegalStateException("Pregunta TF '${q.id}' debe tener exactamente 2 opciones. Fail-closed.")
                    }
                    val optIds = q.options.map { it.id }.toSet()
                    if (optIds != setOf("A", "B")) {
                        throw IllegalStateException("Opciones de pregunta TF '${q.id}' deben ser A, B. Fail-closed.")
                    }
                    if (q.correctOptionId !in setOf("A", "B")) {
                        throw IllegalStateException("correctOptionId inválido '${q.correctOptionId}' en '${q.id}'. Fail-closed.")
                    }
                }
            }

            for (opt in q.options) {
                if (opt.text.isBlank()) {
                    throw IllegalStateException("Opción vacía en pregunta '${q.id}'. Fail-closed.")
                }
            }
        }
    }
}
